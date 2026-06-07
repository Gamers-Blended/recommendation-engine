import logging
from typing import Any

from bson import ObjectId
from bson.errors import InvalidId
from pymongo.asynchronous.database import AsyncDatabase

from app.core.config import get_settings
from app.schemas import ProductResponse

logger = logging.getLogger(__name__)
settings = get_settings()

def _map_doc_to_product(doc: dict[str, Any]) -> ProductResponse:
    """
    Convert a MongoDB document to a ProductResponse

    MongoDB stores _id as ObjectId
    Coerce it to str
    """
    doc["_id"] = str(doc["_id"])
    return ProductResponse.model_validate(doc)

def _parse_object_ids(id_list: list[str]) -> tuple[list[ObjectId], list[str]]:
    """
    Validate and parse string IDs into ObjectIds
    Returns (valid_object_ids, valid_str_ids) - parallel lists
    Malformed IDs are logged and skipped
    """
    object_ids: list[ObjectId] = []
    valid_str_ids: list[str] = []

    for pid in id_list:
        try:
            object_ids.append(ObjectId(pid))
            valid_str_ids.append(pid)
        except (InvalidId, TypeError):
            logger.warrning("Invalid ObjectId, skipping: %s", pid)

    return object_ids, valid_str_ids


class ProductRepository:

    def __init__(self, db: AsyncDatabase) -> None:
        self._products = db[settings.mongo_collection_name]


    async def get_all_products(self) -> list[ProductResponse]:
        """
        Fetch all products from the database and return as list of ProductResponse
        """
        cursor = self._products.find()
        docs = await cursor.to_list(length=None)
        return [_map_doc_to_product(doc) for doc in docs]

    # ------------------------------------------------------------------
    # 1. Signal products — lightweight projection for vector building
    # ------------------------------------------------------------------
    async def get_signal_product_vectors(
            self,
            product_id_list: list[str]
    ) -> dict[str, dict[str, Any]]:
        """
        Fetch only fields needed to build embedding vectors
        Returns {str_id: doc}
        """
        object_ids, valid_str_ids = _parse_object_ids(product_id_list)
        if not object_ids:
            return {}

        pipeline = [
            {"$match": {"_id": {"$in": object_ids}}},
            {
                "$group": {
                    "_id": {
                        "slug": "$slug",
                        "platform": "$platform"
                    },
                    "doc_id": {"$first": "$_id"},
                    "series": {"$first": "$series"},
                    "genres": {"$first": "$genres"},
                    "platform": {"$first": "$platform"}
                }
            },
            {
                "$project": {
                    "_id": "$doc_id",
                    "slug": "$_id.slug",
                    "series": 1,
                    "genres": 1,
                    "platform": 1
                }
            }
        ]

        cursor = await self._products.aggregate(pipeline)

        docs = await cursor.to_list(length=None)
        return {str(doc["_id"]): doc for doc in docs}
    
    # ------------------------------------------------------------------
    # 2. Purchased product IDs — exclusion list
    # ------------------------------------------------------------------
    async def get_purchased_product_ids(self, user_id: str) -> set[str]:
        """
        Return set of product IDs the user has already purchased
        Excluded from recommendations
        """
        # TODO
        return {}
    
    # ------------------------------------------------------------------
    # 3. Full catalogue — for vector matrix (cache-warmed at startup)
    # ------------------------------------------------------------------
    async def get_catalogue_for_indexing(self) -> list[dict[str, Any]]:
        """
        Fetch only embedding fields for ALL products
        Called once at startup and on scheduled cache refresh
        """
        cursor = self._products.find(
            {},
            {"series": 1, "genres": 1, "platform": 1, "slug": 1}
        )
        return await cursor.to_list(length=None)
    
    # ------------------------------------------------------------------
    # 4. Deduplicate by slug+platform — keep highest-ranked product in each group
    # ------------------------------------------------------------------
    # async def dedup_candidates(
    #     self,
    #     ranked_candidate_ids: list[str],
    #     max_results: int
    # ) -> list[str]:
    #     """
    #     Returns deduplicated list of (product_id, score), sorted by score desc
    #     """
    #     object_ids, _ = _parse_object_ids(ranked_candidate_ids)
    #     if not object_ids:
    #         return []
        
    # ------------------------------------------------------------------
    # 4. Full product docs for top-ranked results
    # ------------------------------------------------------------------
    async def get_products_by_ids_ordered(
        self,
        product_id_list: list[str]
    ) -> list[ProductResponse]:

        """
        Fetch products for final recommendation list
        Deduplicate products by slug+platform, keeping the highest-ranked product in each group
        Re-sorts results to match ranked input order
        since MongoDB does not guarantee order of results when using $in operator
        """

        # --- 1. Parse and validate ObjectIds ---
        object_ids, valid_str_ids = _parse_object_ids(product_id_list)
        if not object_ids:
            return []
        
        # --- 2. Preserve rank order as a lookup ---
        rank_order = {pid: idx for idx, pid in enumerate(valid_str_ids)}
        
        # --- 2. Query and aggregate with deduplication by slug+platform ---

        cursor = self._products.find(
            {
                "_id": {"$in": object_ids},
                "stock": {"$gt": 0},  # Only return products that are in stock
            }
        )
        docs = await cursor.to_list(length=None)

        if not docs:
            logger.info(
                "No in-stock products found for IDs: %s", valid_str_ids
            )
            return []
        
        # --- 3. Map to response models ---
        products = [_map_doc_to_product(doc) for doc in docs]
        product_map = {p.id: p for p in products}

        return [product_map[pid] for pid in valid_str_ids if pid in product_map]