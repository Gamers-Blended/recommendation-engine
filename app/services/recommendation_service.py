import logging

from app.repositories.product_repository import ProductRepository
from app.schemas import (
    ProductResponse,
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
