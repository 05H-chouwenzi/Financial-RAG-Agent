"""评估指标单测 —— HitRate@k / Recall@k / MRR / NDCG@k"""
import math

from src.eval.metrics import hit_rate_at_k, mrr, ndcg_at_k, recall_at_k, summarize_retrieval


def test_hit_rate_at_k():
    # 相关文档在 top1 → 命中
    assert hit_rate_at_k([1, 2, 3], {1}, 3) == 1.0
    # 相关文档在 top5 但 k=3 看不到
    assert hit_rate_at_k([1, 2, 3], {5}, 3) == 0.0
    # top-k 外
    assert hit_rate_at_k([1, 2, 3, 4, 5], {6}, 5) == 0.0
    # 空相关集
    assert hit_rate_at_k([1, 2, 3], set(), 3) == 0.0


def test_mrr():
    # 第一个相关文档在第 1 位 → 1.0
    assert mrr([1, 2, 3], {1}) == 1.0
    # 第一个相关文档在第 3 位 → 1/3
    assert abs(mrr([1, 2, 3, 4], {4, 2}) - 1.0 / 2.0) < 1e-9
    # 无命中
    assert mrr([1, 2, 3], {9}) == 0.0


def test_recall_at_k():
    # 3 个相关文档，top5 命中 2 个
    assert abs(recall_at_k([1, 2, 3, 4, 5], {1, 3, 9}, 5) - 2.0 / 3.0) < 1e-9
    # 空相关集 → 0
    assert recall_at_k([1, 2], set(), 2) == 0.0


def test_ndcg_at_k():
    # 理想排序（相关都在最前）→ 1.0
    assert ndcg_at_k([1, 2, 3], {1, 2, 3}, 3) == 1.0
    # 完全不相关 → 0
    assert ndcg_at_k([1, 2, 3], {9}, 3) == 0.0
    # 手工验证：相关在位置 1 和 3
    dcg = 1.0 + 1.0 / math.log2(4)
    idcg = 1.0 + 1.0 / math.log2(3)
    assert abs(ndcg_at_k([1, 5, 2], {1, 2}, 3) - dcg / idcg) < 1e-9


def test_summarize_retrieval():
    ranked = [[1, 2, 3], [9, 1, 2]]
    relevant = [{1}, {1}]
    out = summarize_retrieval(ranked, relevant, top_ks=(3, 5))
    assert out["n"] == 2
    assert out["HitRate@3"] == 1.0  # 两条都在 top3 命中
    assert abs(out["MRR"] - (1.0 + 1.0 / 2.0) / 2.0) < 1e-9
