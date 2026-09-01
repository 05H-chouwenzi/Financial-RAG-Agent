"""中文分词 —— jieba 优先，字符 bigram 兜底（零依赖可运行）"""
from __future__ import annotations


def tokenize(text: str) -> list[str]:
    """分词：jieba 可用则用 jieba，否则用字符 bigram"""
    text = (text or "").strip()
    if not text:
        return []
    try:
        import jieba

        return [t for t in jieba.cut(text) if t.strip()]
    except Exception:  # noqa: BLE001
        if len(text) <= 2:
            return [text]
        return [text[i : i + 2] for i in range(len(text) - 1)]
