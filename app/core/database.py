from pymongo import AsyncMongoClient
from pymongo.asynchronous.database import AsyncDatabase
from app.core.config import get_settings

# Module-level client - instantiated once on startup, reused across requests
# PyMongo's async client manages its own connection pool
_client: AsyncMongoClient | None = None

async def connect_db() -> None:
    """Called on app startup to initialize MongoDB client"""
    global _client
    if _client is None:
        settings = get_settings()
        _client = AsyncMongoClient(settings.mongo_uri)

        # Test the connection
        await _client.admin.command('ping')
        print("Successfully connected to MongoDB")

async def close_db() -> None:
    """Called on app shutdown to close MongoDB client"""
    global _client
    if _client:
        await _client.close()
        _client = None
        print("MongoDB connection closed")

async def get_db() -> AsyncDatabase:
    """
    Dependency-injectable getter
    Raises RuntimeError if called before connect_db
    """
    if _client is None:
        raise RuntimeError("Database client not initialised. connect_db() was not awaited.")
    
    return _client[get_settings().mongo_db_name]