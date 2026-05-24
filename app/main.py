from contextlib import asynccontextmanager
from fastapi import FastAPI

from app.core.database import connect_db, close_db
from app.routers import products

@asynccontextmanager
async def lifespan(app: FastAPI):
    # --- Startup ---
    await connect_db()
    yield

    # --- Shutdown ---
    await close_db()

app = FastAPI(
    title="Product Recommendation Engine API",
    description="Provides personalised product recommendations",
    version="1.0.0",
    lifespan=lifespan
)

app.include_router(products.router, prefix="/api/v1")

@app.get("/health", tags=["Health"])
async def health_check():
    return {"status": "ok"}