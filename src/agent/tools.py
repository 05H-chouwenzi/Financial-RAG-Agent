"""金融计算工具 —— 从检索证据中提取数字计算财务指标

支持的指标：roe（净资产收益率）/ gross_margin（毛利率）/ net_margin（净利率）
          / debt_ratio（资产负债率）/ growth（同比增长率）
"""
from __future__ import annotations

import logging
import re
from typing import Optional

logger = logging.getLogger("agent_tools")

_NUM_KW = re.compile(
    r"([-+]?\d+(?:,\d{3})*(?:\.\d+)?)\s*(亿元|万元|元|%|％|倍)?"
)


def extract_value(text: str, keyword: str) -> Optional[float]:
    """在文本中找 keyword 附近（同行±2行）的数字，返回数值（亿元→万元统一为元？不，保留原数）

    简化：返回数字本身（单位留给调用方判断）。优先取 keyword 所在行。
    """
    lines = text.splitlines()
    hits: list[float] = []
    for i, ln in enumerate(lines):
        if keyword in ln:
            for m in _NUM_KW.finditer(ln):
                num = float(m.group(1).replace(",", ""))
                hits.append(num)
    if not hits:
        return None
    # 取 keyword 所在行出现的第一个数字（表格多列时通常第一列=当前期）
    return hits[0]


def roe(net_profit: float, equity: float) -> float:
    """净资产收益率 ROE = 净利润 / 净资产"""
    return net_profit / equity if equity else 0.0


def gross_margin(revenue: float, cost: float) -> float:
    """毛利率 = (营业收入 - 营业成本) / 营业收入"""
    return (revenue - cost) / revenue if revenue else 0.0


def net_margin(net_profit: float, revenue: float) -> float:
    """净利率 = 净利润 / 营业收入"""
    return net_profit / revenue if revenue else 0.0


def debt_ratio(liabilities: float, assets: float) -> float:
    """资产负债率 = 负债 / 资产"""
    return liabilities / assets if assets else 0.0


def growth(current: float, previous: float) -> float:
    """同比增长率 = (本期 - 上期) / 上期"""
    return (current - previous) / previous if previous else 0.0


CALC_FUNCS = {
    "roe": (roe, ("net_profit", "equity")),
    "gross_margin": (gross_margin, ("revenue", "cost")),
    "net_margin": (net_margin, ("net_profit", "revenue")),
    "debt_ratio": (debt_ratio, ("liabilities", "assets")),
    "growth": (growth, ("current", "previous")),
}

_KW2METRIC = {
    "roe": "roe", "净资产收益率": "roe",
    "毛利率": "gross_margin", "gross margin": "gross_margin",
    "净利率": "net_margin", "净利润率": "net_margin",
    "资产负债率": "debt_ratio",
    "同比增长": "growth", "同比增长率": "growth", "增速": "growth",
}

_KW2FIELD = {
    "roe": [("net_profit", "净利润"), ("equity", "净资产")],
    "gross_margin": [("revenue", "营业收入"), ("cost", "营业成本")],
    "net_margin": [("net_profit", "净利润"), ("revenue", "营业收入")],
    "debt_ratio": [("liabilities", "负债合计"), ("assets", "资产总计")],
    "growth": [("current", "营业收入"), ("previous", "营业收入")],
}


def calc_from_evidence(metric: str, evidence_text: str) -> Optional[dict]:
    """从证据文本中提取所需字段并计算指标

    Returns: {metric, value, fields:{...}} 或 None
    """
    func, args = CALC_FUNCS.get(metric, (None, None))
    if func is None:
        return None
    fields: dict[str, float] = {}
    for arg, kw in _KW2FIELD[metric]:
        v = extract_value(evidence_text, kw)
        if v is None:
            return None
        fields[arg] = v
    try:
        value = func(**fields)
    except Exception as e:  # noqa: BLE001
        logger.warning("计算 %s 失败: %s", metric, e)
        return None
    return {"metric": metric, "value": value, "fields": fields}


def detect_metric(query: str) -> Optional[str]:
    """从问题中识别要计算的指标；识别不到返回 None"""
    q = query.lower()
    for kw, metric in _KW2METRIC.items():
        if kw.lower() in q:
            return metric
    return None
