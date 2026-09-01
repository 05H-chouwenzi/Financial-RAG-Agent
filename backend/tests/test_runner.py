"""评估匹配器单测 —— compute_relevant（doc 命中 / 证据子串 / 关键数字 / 金额单位换算）"""
from src.eval.golden_set import GoldenItem
from src.eval.runner import compute_relevant
from src.chunking.chunker import Chunk


def _chunk(i, text, doc_id="600519/ndbg/600519_2024-04-03_贵州茅台2023年年度报告"):
    return Chunk(chunk_id=f"c{i}", doc_id=doc_id, text=text)


def _item(**kw):
    defaults = dict(id="R01", type="fact", question="q", answer="a",
                    doc_ids="600519/ndbg/600519_2024-04-03_贵州茅台2023年年度报告",
                    evidence="147,693,604,994.14", note="")
    defaults.update(kw)
    return GoldenItem(**defaults)


def test_evidence_substring_match():
    chunks = [_chunk(0, "……营业收入 147,693,604,994.14 元……")]
    rel = compute_relevant(chunks, _item())
    assert rel == {0}


def test_doc_and_number_match():
    # 同 doc、共享关键数字（表格异形同值块）
    chunks = [
        _chunk(0, "主要会计数据 营业收入 147,693,604,994.14"),
        _chunk(1, "审计报告 收入 147,693,604,994.14 确认政策", doc_id="other/doc"),
        _chunk(2, "无关内容"),
    ]
    rel = compute_relevant(chunks, _item(evidence="147,693,604,994.14"))
    assert 0 in rel and 1 not in rel and 2 not in rel


def test_amount_equivalent():
    # 证据 164,699（百万元）↔ 1,646.99亿元
    chunks = [_chunk(0, "营业收入 1,646.99亿元", doc_id="000001/ndbg/000001_2024-03-15_2023年年度报告")]
    rel = compute_relevant(chunks, _item(
        doc_ids="000001/ndbg/000001_2024-03-15_2023年年度报告",
        evidence="164,699"))
    assert 0 in rel


def test_empty_evidence_falls_back_to_doc():
    chunks = [_chunk(0, "任意文本")]
    rel = compute_relevant(chunks, _item(evidence=""))
    assert rel == {0}
