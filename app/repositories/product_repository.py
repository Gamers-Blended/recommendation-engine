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

class ProductRepository:
    def __init__(self, db: AsyncDatabase) -> None:
        self._col = db[settings.mongo_collection_name]


    async def get_all_products(self) -> list[ProductResponse]:
        """
        Fetch all products from the database and return as list of ProductResponse
        """
        cursor = self._col.find()
        docs = await cursor.to_list(length=None)
        return [_map_doc_to_product(doc) for doc in docs]

    # ------------------------------------------------------------------
    # Fetch by IDs (used by recommendation service)
    # ------------------------------------------------------------------

    async def get_products_by_id(
        self,
        product_id_list: list[str],
        preserve_order: bool = True,
        ) -> list[ProductResponse]:

        """
        Fetch products whose _id is in product_ids
        
        preserver_order=True re-sorts results to match input order,
        since MongoDB does not guarantee order of results when using $in operator
        """
        if not product_id_list:
            return []
        
        # --- 1. Parse and validate ObjectIds ---
        object_ids: list[ObjectId] = []
        valid_str_ids: list[str] = [] # parallel list to preserve order mapping

        for pid in product_id_list:
            try:
                object_ids.append(ObjectId(pid))
                valid_str_ids.append(pid)
            except (InvalidId, TypeError):
                logger.warning("Invalid ObjectId format, skipping: %s", pid)
                # continue # skip malformed IDs rather than crashing

        if not object_ids:
            logger.warning("No valid ObjectIds found in product_id_list: %s", product_id_list)
            return []
        
        # --- 2. Query ---
        cursor = self._col.find(
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

        # --- 4. Preserve input order if requested ---
        if preserve_order:
            product_map: dict[str, ProductResponse] = {p.id: p for p in products}
            products = [
                product_map[pid]
                for pid in valid_str_ids
                if pid in product_map
            ]

        return products