"""生成质量检查 —— 数字校验 / 引用溯源 / 拒答

金融场景最忌讳"数字幻觉"：回答中出现的数字必须能在检索证据里找到。
"""
from __future__ import annotations

import re

_NUM_RE = re.compile(r"\d+(?:,\d{3})*(?:\.\d+)?")
_MIN_NUM_LEN = 3  # 过滤过短的数字（如 1、2），减少误报

# 金额单位 → 元 的换算系数（覆盖年报常见口径）
_UNIT_FACTORS = {"亿元": 1e8, "百万元": 1e6, "万元": 1e4, "千元": 1e3, "元": 1.0}
# 证据中"裸数字"可能对应的常见单位（表头标注口径时单元格不带单位）
_COMMON_FACTORS = (1.0, 1e3, 1e4, 1e6, 1e8)
_REL_TOL = 0.01  # 相对容差 1%


def extract_numbers(text: str) -> set[str]:
    """提取文本中的数字（保留原样，便于与证据比对）"""
    return set(_NUM_RE.findall(text or ""))


def _amounts(text: str) -> list[tuple[str, float]]:
    """提取带金额单位的数字 → [(原字符串, 换算为元的数值)]"""
    out = []
    for m in re.finditer(r"(\d+(?:,\d{3})*(?:\.\d+)?)\s*(亿元|百万元|万元|千元|元)?", text or ""):
        raw, unit = m.group(1), m.group(2) or ""
        if unit in _UNIT_FACTORS:
            num = float(raw.replace(",", ""))
            out.append((raw, num * _UNIT_FACTORS[unit]))
    return out


def _amount_hits(ans_yuan: float, ev_text: str) -> bool:
    """回答金额（元）能否在证据中找到：带单位金额直接比对，裸数字按常见单位换算比对"""
    for raw, y in _amounts(ev_text):
        if y and abs(ans_yuan - y) / max(y, 1e-9) <= _REL_TOL:
            return True
    for m in re.finditer(_NUM_RE, ev_text):
        num = m.group(0).replace(",", "")
        if len(num) < _MIN_NUM_LEN:
            continue
        d = float(num)
        for f in _COMMON_FACTORS:
            if abs(ans_yuan - d * f) / max(d * f, 1e-9) <= _REL_TOL:
                return True
    return False


def check_numbers(answer: str, evidences: list[dict]) -> list[str]:
    """回答中出现的数字必须在证据片段中存在；返回未命中的数字列表（空=通过）

    支持单位换算：回答写 1476.94亿元 与证据 14,769,360.50万元 视为一致。
    evidences: [{"text": ...}, ...]
    """
    ans_nums = {n for n in extract_numbers(answer) if len(n) >= _MIN_NUM_LEN}
    if not ans_nums:
        return []
    ev_text = " ".join(ev.get("text", "") for ev in evidences)
    ev_nums = extract_numbers(ev_text)
    ans_amounts = {raw: y for raw, y in _amounts(answer)}
    missing = []
    for n in ans_nums:
        if n in ev_nums or re.fullmatch(r"20\d{2}", n):
            continue  # 精确命中或年份放宽
        if n in ans_amounts and _amount_hits(ans_amounts[n], ev_text):
            continue  # 单位换算命中
        missing.append(n)
    return missing


def ensure_citations(answer: str, evidences: list[dict], max_refs: int = 5) -> str:
    """给回答追加引用来源块（[n] 来源 页码）"""
    refs = []
    for i, ev in enumerate(evidences[:max_refs], 1):
        chunk = ev.get("chunk")
        if chunk is not None:
            source = chunk.friendly_source()  # 公司名+年份+报告类型，而非原始文件路径
            page = chunk.page
        else:
            source = ev.get("source", "未知来源")
            page = ev.get("page", "")
        page_txt = f" 第{page}页" if page else ""
        refs.append(f"[{i}] {source}{page_txt}")
    if not refs:
        return answer.strip()
    block = "\n\n**参考来源：**\n" + "\n".join(refs)
    return answer.strip() + block


def should_refuse(score: float, threshold: float) -> bool:
    """拒答判断：最高分低于阈值"""
    return score < threshold
