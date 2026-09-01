"""生成质量检查单测 —— 数字校验（含单位换算）/ 引用 / 拒答"""
from src.generation.checks import (
    check_numbers,
    ensure_citations,
    extract_numbers,
    should_refuse,
)


def _ev(text):
    return [{"text": text}]


def test_check_numbers_exact():
    # 数字在证据中精确命中 → 通过
    assert check_numbers("营业收入为 1476.94亿元。", _ev("营业收入 1,476.94亿元")) == []
    # 证据没有 → 拦截
    missing = check_numbers("营业收入为 999.99亿元。", _ev("营业收入 1,476.94亿元"))
    assert "999.99" in missing


def test_check_numbers_unit_conversion():
    # 回答 1476.94亿元 ↔ 证据 14,769,360.50万元（单位换算）
    assert check_numbers("营业收入为 1476.94亿元。", _ev("营业收入 14,769,360.50万元")) == []
    # 证据为裸数字，按常见单位枚举可换算
    assert check_numbers("净利润 464.55亿元。", _ev("归属于本行股东的净利润 46,455（百万元）")) == []
    # 答案年份放宽（20xx 不参与数字校验）
    assert check_numbers("2023 年营业收入增长 19.01%。", _ev("本期比上年同期增减(%) 19.01")) == []


def test_check_numbers_blocks_fabrication():
    # 回答中出现证据里没有的数字 → 拦截（防幻觉）
    missing = check_numbers("预计 2030 年营收 8888.88亿元。", _ev("2023 年营业收入 1,476.94亿元"))
    assert missing


def test_extract_numbers():
    nums = extract_numbers("14,769,360.50万元 与 19.01%")
    assert "14,769,360.50" in nums and "19.01" in nums


def test_ensure_citations():
    class FakeChunk:
        def __init__(self, source, page):
            self.source = source
            self.page = page

        def friendly_source(self):
            return "贵州茅台 2023年年度报告"

    ans = ensure_citations("答案", [{"chunk": FakeChunk("x", 5)}])
    assert "[1]" in ans and "贵州茅台 2023年年度报告" in ans and "第5页" in ans


def test_should_refuse():
    assert should_refuse(0.05, 0.10) is True
    assert should_refuse(0.50, 0.10) is False
