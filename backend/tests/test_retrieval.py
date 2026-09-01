"""检索金融增强单测 —— 时间过滤 / 报告类型过滤 / 指标表核心块锚定"""
from src.retrieval.retriever import Retriever, RetrievalConfig
from src.chunking.chunker import Chunk


def _mk(text="", **kw):
    defaults = dict(chunk_id="c0", doc_id="d0", source="x/ndbg/x_2023年年度报告.pdf",
                    title="示例科技2023年年度报告", company="示例科技", text=text,
                    block_type="paragraph", page=1, section_path="主要会计数据",
                    period_year=2023)
    defaults.update(kw)
    return Chunk(**defaults)


def _hits(items):
    """构造 retriever.retrieve 中间阶段的 hit 字典（带 chunk 信息）"""
    out = []
    for i, (idx, score, c) in enumerate(items):
        out.append({"index": idx, "score": score, "text": c.text, "chunk": c,
                    "title": c.title, "source": c.source, "company": c.company,
                    "block_type": c.block_type, "period_year": c.period_year})
    return out


def test_time_filter_keeps_matching_year():
    r = Retriever(chunks=[], config=RetrievalConfig(time_filter=True))
    c23 = _mk(period_year=2023)
    c22 = _mk(period_year=2022)
    hits = _hits([(0, 1.0, c23), (1, 0.9, c22)])
    out = r._apply_time_filter("贵州茅台2023年营收是多少？", hits)
    assert [h["index"] for h in out] == [0]


def test_time_filter_multi_year_no_filter():
    r = Retriever(chunks=[], config=RetrievalConfig(time_filter=True))
    c23 = _mk(period_year=2023)
    c22 = _mk(period_year=2022)
    hits = _hits([(0, 1.0, c23), (1, 0.9, c22)])
    out = r._apply_time_filter("对比2022年和2023年的营收", hits)
    assert len(out) == 2  # 多年度对比不做单年度过滤


def test_report_type_filter_prefers_annual():
    r = Retriever(chunks=[], config=RetrievalConfig(report_type_filter=True))
    annual = _mk(source="x/ndbg/x_2023年年度报告.pdf", title="示例科技2023年年度报告")
    half = _mk(source="x/bndbg/x_2023年半年度报告.pdf", title="示例科技2023年半年度报告")
    hits = _hits([(0, 1.0, annual), (1, 0.9, half)])
    out = r._apply_report_type_filter("2023年年报中的营业收入是多少", hits)
    assert [h["index"] for h in out] == [0]


def test_financial_section_boost_marks_annual_indicator_table():
    r = Retriever(chunks=[], config=RetrievalConfig(financial_boost=2.0, financial_anchor_bonus=0.10))
    # 年报指标表：命中"主要会计数据"表头 → 加权 + 打核心块标记
    annual_tbl = _mk(text="2023年年度报告/(一) 主要会计数据\n营业收入 147,693,604,994.14",
                     source="x/ndbg/x_2023年年度报告.pdf", block_type="paragraph")
    # 半年报指标表：整年问题下不应打核心块标记
    half_tbl = _mk(text="2023年半年度报告/(一) 主要会计数据\n营业收入 69,352,470,272.19",
                   source="x/bndbg/x_2023年半年度报告.pdf")
    # 审计政策段落：不命中指标表头 → 不锚定
    audit = _mk(text="营业收入确认的会计政策……", source="x/ndbg/x_2023年年度报告.pdf")
    hits = _hits([(0, 0.3, annual_tbl), (1, 0.3, half_tbl), (2, 0.3, audit)])
    out = r._apply_financial_section_boost("贵州茅台2023年的营业收入是多少亿元？", hits)

    by_idx = {h["index"]: h for h in out}
    # 年报指标表：加权 ×2 且打标记
    assert by_idx[0]["_fin_anchor"] is True
    assert abs(by_idx[0]["score"] - 0.6) < 1e-9
    # 半年报指标表：整年问题下只加权、不打核心块标记
    assert "_fin_anchor" not in by_idx[1]
    # 审计段落：不锚定
    assert "_fin_anchor" not in by_idx[2]


def test_financial_section_boost_half_year_question_marks_half():
    r = Retriever(chunks=[], config=RetrievalConfig())
    half_tbl = _mk(text="2023年半年度报告/(一) 主要会计数据\n营业收入 69,352,470,272.19",
                   source="x/bndbg/x_2023年半年度报告.pdf")
    hits = _hits([(0, 0.3, half_tbl)])
    out = r._apply_financial_section_boost("贵州茅台2023年上半年的营业收入是多少？", hits)
    assert out[0]["_fin_anchor"] is True


def test_financial_section_boost_skips_gross_margin():
    """毛利率类查询不锚定指标表（答案在分行业/分产品表），避免挤掉正确表格"""
    r = Retriever(chunks=[], config=RetrievalConfig())
    tbl = _mk(text="2023年年度报告/(一) 主要会计数据\n毛利率 91.54%",
              source="x/ndbg/x_2023年年度报告.pdf")
    hits = _hits([(0, 0.3, tbl)])
    out = r._apply_financial_section_boost("贵州茅台2023年酒类业务的整体毛利率是多少？", hits)
    assert "_fin_anchor" not in out[0]
