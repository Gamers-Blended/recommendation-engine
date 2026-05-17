from pydantic import BaseModel, Field
from typing import List, Optional

class RecommendationRequest(BaseModel):
    user_id: str
    product_id: str
    limit: Optional[int] = Field(default=10, ge=1, le=50)

class RecommendationProduct(BaseModel):
    product_id: str
    score: float

class RecommendationResponse(BaseModel):
    user_id: str
    recommendations: List[RecommendationProduct]
    source: str