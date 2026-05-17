import redis.asyncio as redis
import json
from app.core.config import settings

class CacheService:
    def __init__(self):
        self.client = redis.from_url(settings.redis_url, decode_responses=True)

    def _key(self, user_id: str, product_id: str) -> str:
        return f"reco:{user_id}:{product_id}"
    
    async def get(self, user_id: str, product_id: str):
        data = await self.client.get(self._key(user_id, product_id))
        return json.loads(data) if data else None
    
    async def set(self, user_id: str, product_id: str, value: list):
        await self.client.setex(
            self._key(user_id, product_id),
            settings.cache_ttl_seconds,
            json.dumps(value)
        )

    async def invalidate(self, user_id: str, product_id: str):
        await self.client.delete(self._key(user_id, product_id))

cache_service = CacheService()