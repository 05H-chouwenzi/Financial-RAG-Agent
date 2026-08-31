"""结果融合 —— RRF 与加权分数融合

统一约定：hit = {"index": int, "score": float, "text": str, "meta": dict}
index 是 chunk 在 corpus 中的位置，稠密/稀疏两路共用，保证可对齐。
"""
from __future__ import annotations

from typing import Iterable


def fuse_rrf(ranked_lists: Iterable[list[dict]], k: int = 60, top_k: int = 10) -> list[dict]:
    """Reciprocal Rank Fusion：score = Σ 1/(k + rank)

    优点：不依赖分数绝对值，两路分数尺度不一致时依然稳健。
    """
    agg: dict[int, dict] = {}
    for lst in ranked_lists:
        for rank, item in enumerate(lst, start=1):
            idx = item["index"]
            entry = agg.setdefault(idx, {"score": 0.0, "item": item})
            entry["score"] += 1.0 / (k + rank)
    ranked = sorted(agg.items(), key=lambda kv: kv[1]["score"], reverse=True)
    return [{**v["item"], "score": v["score"]} for _, v in ranked[:top_k]]


def fuse_weighted(
    dense_hits: list[dict],
    sparse_hits: list[dict],
    w_dense: float = 0.5,
    w_sparse: float = 0.5,
    top_k: int = 10,
) -> list[dict]:
    """加权分数融合：需要两路分数尺度接近（如都是归一化余弦）"""
    agg: dict[int, dict] = {}
    for w, hits in ((w_dense, dense_hits), (w_sparse, sparse_hits)):
        if w <= 0:
            continue
        for item in hits:
            idx = item["index"]
            entry = agg.setdefault(idx, {"score": 0.0, "item": item})
            entry["score"] += w * item["score"]
    ranked = sorted(agg.items(), key=lambda kv: kv[1]["score"], reverse=True)
    return [{**v["item"], "score": v["score"]} for _, v in ranked[:top_k]]


def fuse_default(dense_hits: list[dict], sparse_hits: list[dict], top_k: int = 10) -> list[dict]:
    """默认融合：RRF（对分数尺度不敏感，推荐默认）"""
    return fuse_rrf([dense_hits, sparse_hits], top_k=top_k)
