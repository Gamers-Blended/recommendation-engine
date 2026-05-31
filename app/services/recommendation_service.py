import logging
from datetime import datetime, timezone
from typing import NamedTuple

from app.core.cache import cache
from app.core.config import get_settings
from app.repositories.product_repository import ProductRepository
from app.schemas import (
    ProductResponse,
    ProductRecommendation,
    RecommendationRequest,
    RecommendationResponse,
    SignalType,
)

logger = logging.getLogger(__name__)

class RecommendationService:
    """
    Encapsulates all recommendation business logic

    Decide whether to serve personalised recommendations or best sellers
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
        product_response_list = await self._repo.get_products_by_id(request.product_id_list, preserve_order=True)

        mapped_product_list = [
            ProductRecommendation(
                product_id=p.id,
                name=p.name,
                slug=p.slug,
                platform=p.platform,
                region=p.region,
                edition=p.edition,
                price=p.price,
                product_image_url=p.product_image_url,
            )
            for p in product_response_list
        ]

        return RecommendationResponse(
            products = mapped_product_list,
            total = len(mapped_product_list)
        )
                