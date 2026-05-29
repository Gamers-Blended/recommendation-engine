import logging
from typing import Any

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

    # return ProductResponse(
    #     id=doc.get("_id"),
    #     name=doc.get("name"),
    #     description=doc.get("description"),
    #     price=doc.get("price"),
    #     category=doc.get("category"),
    #     image_url=doc.get("image_url")
    # )

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
        product_ids: list[str],
        *,
        preserve_order: bool = True,
        ) -> list[ProductResponse]:

        """
        Fetch products whose _id is in product_ids
        
        preserver_order=True re-sorts results to match input order,
        since MongoDB does not guarantee order of results when using $in operator
        """
        if not product_ids:
            return []
        
        from bson import ObjectId

        # Silently skip any IDs that are not valid ObjectIds
        object_ids: list[ObjectId] = []
        for product_id in product_ids:
            try:
                object_ids.append(ObjectId(product_id))
            except Exception as e:
                logger.warning(f"Skipping invalid product ID: {product_id} - {e}")

        if not object_ids:
            return []
        
        cursor = self._col.find(
            {"_id": {"$in": object_ids}, "stock": {"$gt": 0}},  # Only return products that are in stock
        )
        docs = await cursor.to_list(length=len(object_ids))
        products = [_map_doc_to_product(doc) for doc in docs]

        if preserve_order:
            # Create a mapping of product_id to product
            product_map = {product.id: product for product in products}
            # Reorder products to match the input order of product_ids
            products = [product_map.get(product_id) for product_id in product_ids if product_id in product_map]

        return products