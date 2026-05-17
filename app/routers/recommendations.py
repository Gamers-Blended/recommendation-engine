from fastapi import APIRouter, Depends, HTTPException, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.models.schemas import RecommendationRequest, RecommendationResponse
from app.services.recommendation_engine import recommendation_engine
from app.services.cache import cache_service
from app.db.mongo import get_db
from app.config import settings
import logging

router = APIRouter(prefix="/recommendations", tags=["recommendations"])
logger = logging.getLogger(__name__)
security = HTTPBearer()

def verify_secret(credentials: HTTPAuthorizationCredentials = Security(security)):
    if credentials.credentials != settings.service_secret:
        raise HTTPException(status_code=401, detail="Invalid service token")
    
@router.get("", response_model=RecommendationResponse)
async def get_recommendations(
    user_id: str,
    product_id: str,
    limit: int = 10,
    db=Depends(get_db),
    _=Depends(verify_secret)
):
    # 1. Check cache
    cached = await cache_service.get(user_id, product_id)
    if cached:
        logger.info(f"Cache hit for user {user_id} and product {product_id}")
        return RecommendationResponse(
            user_id=user_id,
            recommendations=cached,
            source="cache"
        )
    
    # 2. Compute recommendations
    try:
        recommendations = await recommendation_engine.get_recommendations(
            db, user_id, product_id, limit
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.exception("Recommendation computation failed")
        raise HTTPException(status_code=500, detail="Internal error")
    
    # 3. Cache results
    await cache_service.set(user_id, product_id, [rec.dict() for rec in recommendations])
    
    return RecommendationResponse(
        user_id=user_id,
        recommendations=recommendations,
        source="computed"
    )