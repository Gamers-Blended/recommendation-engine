from motor.motor_asyncio import AsyncIOMotorClient
from app.core.config import settings

class MongoDB:
    client: AsyncIOMotorClient = None

db = MongoDB()

async def connect_db():
    db.client = AsyncIOMotorClient(settings.mongo_uri)

async def close_db():
    db.client.close()

def get_db():
    return db.client[settings.mongo_db]