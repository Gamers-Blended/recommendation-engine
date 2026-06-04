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
        
        cursor = self._products.find(
            {"_id": {"$in": object_ids}},
            {"series": 1, "genres": 1, "platform": 1}
        )
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
            {"series": 1, "genres": 1, "platform": 1}
        )
        return await cursor.to_list(length=None)
    
    # ------------------------------------------------------------------
    # 4. Full product docs for top-ranked results
    # ------------------------------------------------------------------
    async def get_products_by_ids_ordered(
        self,
        product_id_list: list[str]
    ) -> list[ProductResponse]:

        """
        Fetch product documents for final recommendation list
        Re-sorts results to match ranked input order
        since MongoDB does not guarantee order of results when using $in operator
        """

        # --- 1. Parse and validate ObjectIds ---
        object_ids, valid_str_ids = _parse_object_ids(product_id_list)
        if not object_ids:
            return []
        
        # --- 2. Query ---
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