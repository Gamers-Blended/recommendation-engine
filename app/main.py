import logging

from contextlib import asynccontextmanager
from fastapi import FastAPI

from app.core.cache import close_cache, connect_cache
from app.core.config import get_settings
from app.core.database import connect_db, close_db
from app.services.cache_keys import invalidate_catalogue_cache
from app.routers import products

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s - %(message)s"
)
logger = logging.getLogger(__name__)
settings = get_settings()


# ---------------------------------------------------------------------------
# Lifespan
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    # --- Startup ---
    logger.info("Connecting to MongoDB...")
    await connect_db()
    logger.info("Connecting to Redis...")
    await connect_cache()
    await invalidate_catalogue_cache()
    logger.info("Ready.")
    yield

    # --- Shutdown ---
    logger.info("Shutting down...")
    await close_cache()
    await close_db()
    logger.info("Goodbye!")


# ---------------------------------------------------------------------------
# App factory
# ---------------------------------------------------------------------------

app = FastAPI(
    title="Product Recommendation Engine API",
    description="Provides personalised product recommendations",
    version="1.0.0",
    lifespan=lifespan
)


# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------

app.include_router(products.router, prefix="/api/v1")


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------

@app.get("/health", tags=["Health"])
async def health_check():
    return {"status": "ok"}