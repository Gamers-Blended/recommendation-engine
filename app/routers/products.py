from fastapi import APIRouter, status, Depends
from pymongo.asynchronous.database import AsyncDatabase

from app.core.database import get_db
from app.repositories.product_repository import ProductRepository
from app.schemas import ProductResponse
from app.services.recommendation_service import RecommendationService

router = APIRouter(prefix="/products", tags=["Products"])

def get_product_repo(db: AsyncDatabase = Depends(get_db)) -> ProductRepository:
    return ProductRepository(db)

def get_recommendation_service(repo: ProductRepository = Depends(get_product_repo)) -> RecommendationService:
    return RecommendationService(repo)

@router.get("/",
            response_model=list[ProductResponse],
            description="Get all products",
            status_code=status.HTTP_200_OK
)
async def get_all_products(service: RecommendationService = Depends(get_recommendation_service)):
    return await service.get_all_products()