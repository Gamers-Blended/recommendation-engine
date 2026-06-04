import logging
from datetime import datetime, timezone
from typing import Any

import numpy as np

from app.core.config import get_settings
from app.core.cache import cache
from app.repositories.product_repository import ProductRepository
from app.schemas import (
    ProductResponse,
    ProductRecommendation,
    RecommendationRequest,
    RecommendationResponse,
    SignalType,
)
from app.services.embeddings import (
    build_vocab,
    build_product_vector,
    cosine_similarity_matrix
)
from app.services.scoring import build_query_vector, rank_candidates

logger = logging.getLogger(__name__)
settings = get_settings()

_CACHE_KEY_VOCAB = "recommendation:catalogue:vocab"
_CACHE_KEY_IDS = "recommendation:catalogue:ids"
_CACHE_KEY_MATRIX = "recommendation:catalogue:matrix"
_CACHE_TTL_SECONDS = 3600

_SIGNAL_WEIGHTS: dict[SignalType, float] = {
    SignalType.PURCHASE:  3.0,
    SignalType.CART_ADD:  2.0,
    SignalType.WISHLIST:  2.0,
    SignalType.BROWSE:    1.0,
}

async def _warm_catalogue_cache(repo: ProductRepository) -> tuple[dict[str, int], list[str], np.ndarray]:
    """
    Load catalogue vectors from Redis
    On miss, rebuild from MongoDB and repopulate cache
    All 3 keys are written atomically to avoid partial cache states
    """
    vocab = await cache.get(_CACHE_KEY_VOCAB)
    ids = await cache.get(_CACHE_KEY_IDS)
    matrix = await cache.get(_CACHE_KEY_MATRIX)

    if vocab is not None and ids is not None and matrix is not None:
        return vocab, ids, matrix
    
    logger.info("Catalogue cache miss, rebuilding from DB...")
    products = await repo.get_catalogue_for_indexing()

    vocab = build_vocab(products)
    matrix = np.array(
        [build_product_vector(p, vocab) for p in products],
        dtype=np.float32
    )
    ids = [str(p["_id"]) for p in products]

    # Cache all 3 components atomically
    await cache.set(_CACHE_KEY_VOCAB, vocab, ttl_seconds=_CACHE_TTL_SECONDS)
    await cache.set(_CACHE_KEY_IDS, ids, ttl_seconds=_CACHE_TTL_SECONDS)
    await cache.set(_CACHE_KEY_MATRIX, matrix, ttl_seconds=_CACHE_TTL_SECONDS)

    logger.info("Catalogue cached: %d products, vocab=%d", len(ids), len(vocab))
    return vocab, ids, matrix


class RecommendationService:
    """
    Encapsulates all recommendation business logic

    Pre-process, deduplicate and score signals
    Delegate DB access to ProductRepository
    Cache results at both best-sellers and per-user/session level
    """

    def __init__(self, repo: ProductRepository) -> None:
        self._repo = repo


    # ------------------------------------------------------------------
    # Test entry point
    # ------------------------------------------------------------------
    
    async def get_all_products(self) -> list[ProductResponse]:
        return await self._repo.get_all_products()


    # ------------------------------------------------------------------
    # Public entry point
    # ------------------------------------------------------------------

    async def get_recommendations(
            self, request: RecommendationRequest
    ) -> RecommendationResponse:
        
        # ── 0. Load catalogue  ──────────────────────────────────────────
        vocab, catalogue_ids, matrix = await _warm_catalogue_cache(self._repo)

        # ── 1. Fetch signal product docs (embedding fields only) ────────
        signal_docs = await self._repo.get_signal_product_vectors(request.product_id_list)

        if not signal_docs:
            logger.info("No signal products resolved")
            return RecommendationResponse(
                products=[],
                total = 0
            )
        
        # ── 2. Build weighted query vector ──────────────────────────────
        signals = self._build_signals(request, signal_docs)
        query_vec = build_query_vector(signals, vocab, len(vocab))

        if np.linalg.norm(query_vec) == 0:
            logger.warning("Zero query vector")
            return RecommendationResponse(
                products=[],
                total = 0
            )

        # ── 3-6. Similarity → rank → exclude → hydrate──────────────────
        sim_scores = cosine_similarity_matrix(query_vec.reshape(1, -1), matrix).flatten()
        purchased_ids = await self._get_purchased_ids(request)
        top_ranked = rank_candidates(sim_scores, catalogue_ids, purchased_ids, request.max_results)
        
        if not top_ranked:
            logger.info("No candidates after ranking and exclusion")
            return RecommendationResponse(
                products=[],
                total = 0
            )
        
        products = await self._repo.get_products_by_ids_ordered([pid for pid, _ in top_ranked])

        return RecommendationResponse(
            products = [self._to_recommendation(p) for p in products],
            total = len(products)
        )
                

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------
    def _build_signals(
            self,
            request: RecommendationRequest,
            signal_docs: dict[str, dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """
        Map product_id_list to signal dicts consumed by build_query_vector
        Defaults to BROWSE type since RecommendationRequest carries no signal metadata
        """
        return [
            {
                "product": doc,
                "type": SignalType.BROWSE.value,
                "timestamp": datetime.now(tz=timezone.utc),
                "weight": 1
            }
            for pid, doc in signal_docs.items()
        ]

    async def _get_purchased_ids(self, request: RecommendationRequest) -> set[str]:
        if request.user_id:
            return await self._repo.get_purchased_product_ids(request.user_id)
        return set()
    
    @staticmethod
    def _to_recommendation(p: Any) -> ProductRecommendation:
        return ProductRecommendation(
            product_id=p.id,
            name=p.name,
            slug=p.slug,
            platform=p.platform,
            region=p.region,
            edition=p.edition,
            price=p.price,
            product_image_url=p.product_image_url
        )