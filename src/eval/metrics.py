"""检索/生成评估指标 —— 纯 Python 实现

检索：HitRate@k / Recall@k / MRR / NDCG
生成：数字校验通过率、拒答准确率（可选 RAGAS，见 ragas_eval.py）
"""
from __future__ import annotations

import math


def hit_rate_at_k(ranked_indices: list[int], relevant: set[int], k: int) -> float:
    """top-k 中是否命中至少一个相关文档（按样本平均）"""
    top = ranked_indices[:k]
    return 1.0 if any(i in relevant for i in top) else 0.0


def recall_at_k(ranked_indices: list[int], relevant: set[int], k: int) -> float:
    """top-k 命中的相关文档数 / 总相关文档数"""
    if not relevant:
        return 0.0
    top = ranked_indices[:k]
    return sum(1 for i in top if i in relevant) / len(relevant)


def mrr(ranked_indices: list[int], relevant: set[int]) -> float:
    """第一个相关文档的倒数排名；无命中返回 0"""
    for rank, i in enumerate(ranked_indices, 1):
        if i in relevant:
            return 1.0 / rank
    return 0.0


def ndcg_at_k(ranked_indices: list[int], relevant: set[int], k: int) -> float:
    """NDCG@k（二值相关）"""
    top = ranked_indices[:k]
    dcg = sum(1.0 / math.log2(rank + 1) for rank, i in enumerate(top, 1) if i in relevant)
    # 理想排序：相关文档排最前
    n_rel = min(len(relevant), k)
    idcg = sum(1.0 / math.log2(rank + 1) for rank in range(1, n_rel + 1))
    return dcg / idcg if idcg > 0 else 0.0


def mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def summarize_retrieval(
    ranked_lists: list[list[int]],
    relevant_sets: list[set[int]],
    top_ks=(3, 5, 10),
) -> dict:
    """汇总一批查询的检索指标

    ranked_lists[i]: 第 i 个查询的排序后的 chunk index 列表
    relevant_sets[i]: 第 i 个查询的相关 chunk index 集合
    """
    n = len(ranked_lists)
    out: dict = {"n": n}
    for k in top_ks:
        out[f"HitRate@{k}"] = mean([
            hit_rate_at_k(rl, rs, k) for rl, rs in zip(ranked_lists, relevant_sets)
        ])
        out[f"Recall@{k}"] = mean([
            recall_at_k(rl, rs, k) for rl, rs in zip(ranked_lists, relevant_sets)
        ])
    out["MRR"] = mean([mrr(rl, rs) for rl, rs in zip(ranked_lists, relevant_sets)])
    out["NDCG@5"] = mean([ndcg_at_k(rl, rs, 5) for rl, rs in zip(ranked_lists, relevant_sets)])
    return out
