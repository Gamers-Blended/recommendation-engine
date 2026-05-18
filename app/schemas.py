from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List, Set
from decimal import Decimal
from datetime import date

class ProductBase(BaseModel):
    name: str
    slug: str
    description: str
    price: Decimal
    platform: str
    region: str
    edition: str
    publisher: str
    release_date: date
    series: Set[str]
    genres: Set[str]
    languages: Set[str]
    number_of_players: Set[str]
    weight: Decimal
    units_sold: int
    stock: int
    product_image_url: str
    image_url_list: List[str]
    edition_notes: Optional[str] = None
    created_on: date

class ProductResponse(ProductBase):
    model_config = ConfigDict(
        populate_by_name=True,
        json_encoders={Decimal: str}
    )
    
    id: str = Field(..., alias="_id")

