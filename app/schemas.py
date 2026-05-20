from pydantic import BaseModel, Field, ConfigDict, field_serializer
from typing import Optional, List, Set
from decimal import Decimal
from datetime import date, datetime
from enum import Enum

# --- Enums ---

class SignalType(str, Enum):
    BROWSE = "BROWSE"
    PURCHASE = "PURCHASE"
    CART_ADD = "CART_ADD"
    WISHLIST = "WISHLIST"

class UserSegment(str, Enum):
    NEW = "NEW"
    RETURNING = "RETURNING"
    GUEST = "GUEST"

# --- Recommendation schemas ---

class ProductSignal(BaseModel):
    product_id: str
    type: SignalType
    timestamp: datetime
    weight: int = Field(default=1, ge=1, le=10)

class RecommendationRequest(BaseModel):
    user_id: Optional[str] = None
    session_id: str
    signal_list: List[ProductSignal]
    user_segment: UserSegment
    max_results: int = Field(default=20, ge=1, le=100)

# --- Product schemas ---

class ProductBase(BaseModel):
    name: str
    slug: str
    description: str
    price: Decimal = Field(..., ge=0, decimal_places=2)
    platform: str
    region: str
    edition: str
    publisher: str
    release_date: date
    series: Set[str]
    genres: Set[str]
    languages: Set[str]
    number_of_players: Set[str]
    weight: Decimal = Field(..., ge=0, decimal_places=2)
    units_sold: int = Field(..., ge=0)
    stock: int = Field(..., ge=0)
    product_image_url: str
    image_url_list: List[str]
    edition_notes: Optional[str] = None
    created_on: datetime

class ProductResponse(ProductBase):
    model_config = ConfigDict(populate_by_name=True)
    
    id: str = Field(..., alias="_id")

    @field_serializer("price", "weight")
    def serialize_decimal(self, value: Decimal) -> str:
        return str(value)
