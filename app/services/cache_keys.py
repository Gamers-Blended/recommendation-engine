from app.core.cache import cache

CACHE_KEY_VOCAB = "recommendation:catalogue:vocab"
CACHE_KEY_IDS = "recommendation:catalogue:ids"
CACHE_KEY_MATRIX = "recommendation:catalogue:matrix"
CACHE_TTL_SECONDS = 3600

async def invalidate_catalogue_cache() -> None:
    """Helper to invalidate all catalogue cache keys, called on startup and after DB updates."""
    await cache.delete(CACHE_KEY_VOCAB)
    await cache.delete(CACHE_KEY_IDS)
    await cache.delete(CACHE_KEY_MATRIX)