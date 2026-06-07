from __future__ import annotations
from datetime import datetime, timezone
from typing import Any

from app.schemas import SignalType
import numpy as np

# ---------------------------------------------------------------------------
# Signal priority: PURCHASE > CART_ADD > BROWSE
# WISHLIST is treated the same as CART_ADD
# ---------------------------------------------------------------------------
SIGNAL_WEIGHTS: dict[SignalType, float] = {
    SignalType.PURCHASE:  3.0,
    SignalType.CART_ADD:  2.0,
    SignalType.WISHLIST:  2.0,
    SignalType.BROWSE:    1.0,
}

# How quickly older signal decay (in days)
# λ = ln(2) / half_life_days
HALF_LIFE_DAYS = 30.0
_LAMBDA = 0.693147 / HALF_LIFE_DAYS


def time_decay(ts: datetime, now: datetime | None = None) -> float:
    """
    Exponential time decay: recent signals matter more
    Returns mutliplier in (0, 1]
    """
    if now is None:
        now = datetime.now(tz=timezone.utc)
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)
    age_days = max((now - ts).total_seconds() / 86400, 0)
    return float(np.exp(-_LAMBDA * age_days))

def build_query_vector(
        signals: list[dict[str, Any]],
        vocab: dict[str, int],
        vector_size: int
) -> np.ndarray:
    """
    Aggregate signal products into a single weighted query vector
    
    signal["weight"] - user-supplied weight field from ProductSignal (1-10)
    SIGNAL_WEIGHTS - type-based multiplier (PURCAHSE > CART_ADD > BROWSE)
    time_decay() - recency multiplier
    """
    from .embeddings import build_product_vector # avoid circular import

    agg = np.zeros(vector_size, dtype=np.float32)

    for sig in signals:
        product_vec = build_product_vector(sig["product"], vocab)
        type_w = SIGNAL_WEIGHTS.get(sig["type"], 1.0)
        user_w = float(sig.get("weight", 1))
        decay = time_decay(sig["timestamp"])
        agg += product_vec * type_w * user_w * decay

    # Avoid zero vector (e.g. unknown products)
    if np.linalg.norm(agg) == 0:
        return agg
    return agg

def rank_candidates(
        similarity_scores: np.ndarray, # shape (N,)
        candidate_ids: list[str],
        excluded_ids: set[str], # already-purchased products
        max_results: int,
        dedup_keys: dict[str, tuple[str, str]] | None = None # id -> (slug, platform)
) -> list[tuple[str, float]]:
    """
    Filter excluded products, then return top-k by score
    Returns list of (product_id, score) sorted descending
    """
    scored = [
        (cid, float(similarity_scores[i]))
        for i, cid in enumerate(candidate_ids)
        if cid not in excluded_ids
    ]
    scored.sort(key=lambda x: x[1], reverse=True)

    if not dedup_keys:
        return scored[:max_results]
    
    # Walk in rank order, skip seen slug+platform combinations until we have enough results
    seen_combinations = set()
    results = []
    for cid, score in scored:
        key = dedup_keys.get(cid)
        if key is None or key not in seen_combinations:
            if key:
                seen_combinations.add(key)
            results.append((cid, score))
            if len(results) >= max_results:
                break

    return results