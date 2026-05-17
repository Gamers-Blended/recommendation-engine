from motor.motor_asyncio import AsyncIOMotorDatabase
from sklearn.metrics.pairwise import cosine_similarity
from app.models.schemas import RecommendationProduct
import numpy as np
import logging

logger = logging.getLogger(__name__)

class RecommendationEngine:
    async def get_recommendations(
            self,
            db: AsyncIOMotorDatabase,
            user_id: str,
            product_id: str,
            limit: int
    ) -> list[RecommendedProduct]:
        # 1. Fetch anchor product
        anchor = await db.products.find_one({"_id": product_id})
        if not anchor:
            raise ValueError(f"Product {product_id} not found")
        
        # 2. Fetch user purchase history
        orders = await db.orders.find(
            {"userId": user_id},
            {"productIds": 1}
        ).to_list(length=100)
        purchased_ids = {pid for order in orders for pid in order.get("productIds", [])}

        # 3. Candidate retrieval - same category, not already purchased
        candidates = await db.products.find({
            "category": anchor["category"],
            "_id": {"$nin": list(purchased_ids | {product_id})}
        }).to_list(length=200)

        if not candidates:
            return []
        
        # 4. Score by tag overlap
        anchor_tags = set(anchor.get("tags", []))
        results = []
        for candidate in candidates:
            candidate_tags = set(candidate.get("tags", []))
            overlap = len(anchor_tags & candidate_tags)
            total = len(anchor_tags | candidate_tags) or 1
            score = round(overlap / total, 4)
            results.append(RecommendedProduct(
                product_id=str(candidate["_id"]),
                score=score,
                reason="similar tags in same category"
            ))

        # 5. Sort by score, return top N
        results.sort(key=lambda x: x.score, reverse=True)
        return results[:limit]
    
recommendation_engine = RecommendationEngine()