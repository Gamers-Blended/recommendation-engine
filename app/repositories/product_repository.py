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
