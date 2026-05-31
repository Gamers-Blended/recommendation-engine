import logging

from fastapi import APIRouter, Depends, HTTPException, status
from pymongo.asynchronous.database import AsyncDatabase

from app.core.database import get_db
from app.repositories.product_repository import ProductRepository
from app.schemas import ProductResponse, RecommendationRequest, RecommendationResponse
from app.services.recommendation_service import RecommendationService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/products", tags=["Products"])


# ---------------------------------------------------------------------------
# Dependency factories
# ---------------------------------------------------------------------------

def get_product_repo(db: AsyncDatabase = Depends(get_db)) -> ProductRepository:
    return ProductRepository(db)

def get_recommendation_service(repo: ProductRepository = Depends(get_product_repo)) -> RecommendationService:
    return RecommendationService(repo)


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.get("/",
            response_model=list[ProductResponse],
            description="Get all products",
            status_code=status.HTTP_200_OK
)
async def get_all_products(service: RecommendationService = Depends(get_recommendation_service)):
    return await service.get_all_products()

@router.post(
    "/",
    response_model=RecommendationResponse,
    summary="Get product recommendations",
    description="Get personalised product recommendations based on user signals and segment",
    status_code=status.HTTP_200_OK
)
async def get_recommendations(
    request: RecommendationRequest,
    service: RecommendationService = Depends(get_recommendation_service)
) -> RecommendationResponse:
    """
    POST /recommendations    
    """
    try:
        return await service.get_recommendations(request)
    except Exception as e:
        # Spring Boot circuit breaker will catch 500 and fall back to its own best-sellers cache
        logger.exception("Unexpected error in recommendation service: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Recommendation service encountered an unexpected error."
        )