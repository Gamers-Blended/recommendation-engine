from fastapi import APIRouter, HTTPException, Request, status
from app.schemas import ProductBase, ProductResponse

router = APIRouter(prefix="/products", tags=["Products"])

@router.get("/", response_model=list[ProductResponse], status_code=status.HTTP_200_OK)
async def get_all_products(request: Request):
    db = request.app.state.db
    collection = db["products"]
    products = await collection.find().to_list(length=None)
    return products