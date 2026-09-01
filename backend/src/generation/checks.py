"""生成质量检查 —— 数字校验 / 引用溯源 / 拒答

金融场景最忌讳"数字幻觉"：回答中出现的数字必须能在检索证据里找到。
"""
from __future__ import annotations

import re

_NUM_RE = re.compile(r"\d+(?:\.\d+)?")
_MIN_NUM_LEN = 3  # 过滤过短的数字（如 1、2），减少误报


def extract_numbers(text: str) -> set[str]:
    """提取文本中的数字（保留原样，便于与证据比对）"""
    return set(_NUM_RE.findall(text or ""))


def check_numbers(answer: str, evidences: list[dict]) -> list[str]:
    """回答中出现的数字必须在证据片段中存在；返回未命中的数字列表（空=通过）

    evidences: [{"text": ...}, ...]
    """
    ans_nums = {n for n in extract_numbers(answer) if len(n) >= _MIN_NUM_LEN}
    if not ans_nums:
        return []
    ev_text = " ".join(ev.get("text", "") for ev in evidences)
    ev_nums = extract_numbers(ev_text)
    # 年份(4位20xx)视为常见引用背景，放宽
    missing = [n for n in ans_nums if n not in ev_nums and not re.fullmatch(r"20\d{2}", n)]
    return missing


def ensure_citations(answer: str, evidences: list[dict], max_refs: int = 5) -> str:
    """给回答追加引用来源块（[n] 来源 页码）"""
    refs = []
    for i, ev in enumerate(evidences[:max_refs], 1):
        chunk = ev.get("chunk")
        source = chunk.source if chunk else ev.get("source", "未知来源")
        page = chunk.page if chunk else ev.get("page", "")
        page_txt = f" 第{page}页" if page else ""
        refs.append(f"[{i}] {source}{page_txt}")
    if not refs:
        return answer.strip()
    block = "\n\n**参考来源：**\n" + "\n".join(refs)
    return answer.strip() + block


def should_refuse(score: float, threshold: float) -> bool:
    """拒答判断：最高分低于阈值"""
    return score < threshold
