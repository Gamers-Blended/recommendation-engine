from __future__ import annotations
import hashlib
from typing import Any

import numpy as np
from sklearn.preprocessing import normalize

# ---------------------------------------------------------------------------
# Field weights: how much each MongoDB product field contributes to the vector
# ---------------------------------------------------------------------------
FIELD_WEIGHTS: dict[str, float] = {
    "series": 3.0, # highest
    "genres": 2.0,
    "platform": 1.0
}

def _stable_hash_token(token: str) -> int:
    """Deterministic int hash of a string token (no randomness across restarts)"""
    return int(hashlib.md5(token.encode()).hexdigest(), 16)

def build_product_vector(product: dict[str, Any], vocab: dict[str, int]) -> np.ndarray:
    """
    Build weighted sparse vector for 1 product
    
    `vocab` - maps token strings to column indices
    Returns 1-D float32 numpy array of length len(vocab)
    """
    vec = np.zeros(len(vocab), dtype=np.float32)

    for field, weight in FIELD_WEIGHTS.items():
        values: set[str] = product.get(field) or set()
        if isinstance(values, str):
            values = {values}
        for val in values:
            token = f"{field}:{val.lower().strip()}"
            if token in vocab:
                vec[vocab[token]] += weight # accumulate (a product may appear in multiple genres)

    return vec

def build_vocab(products: list[dict[str, Any]]) -> dict[str, int]:
    """
    One-pass vocab construction from a product catalogue
    Call once at startup / cache refresh, not per request
    """
    tokens: set[str] = set()
    for p in products:
        for field in FIELD_WEIGHTS:
            values = p.get(field) or set()
            if isinstance(values, str):
                values = {values}
            for val in values:
                tokens.add(f"{field}:{val.lower().strip()}")

    return {tok: idx for idx, tok in enumerate(sorted(tokens))}

def cosine_similarity_matrix(
        query_vecs: np.ndarray, # (Q, D)
        catalogue_vecs: np.ndarray, # (N, D)
) -> np.ndarray: # (Q, N)
    """
    Batch consine similarity
    Both matrices are L2-normalised first
    Safe against zero-vectors (returns 0 similarity)
    """
    q_norm = normalize(query_vecs, norm="l2", axis=1)
    c_norm = normalize(catalogue_vecs, norm="l2", axis=1)
    return q_norm @ c_norm.T # (Q, N)