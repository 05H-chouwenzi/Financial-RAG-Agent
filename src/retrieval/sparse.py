"""BM25 稀疏检索 —— 纯 Python 实现（零依赖，可讲清原理）

BM25 公式：score(d,q) = Σ idf(t) * (tf·(k1+1)) / (tf + k1·(1-b+b·|d|/avgdl))
说明：实现标准 Okapi BM25，配合 jieba 分词。如需更大规模可换 bm25s/Elasticsearch。
"""
from __future__ import annotations

import json
import math
from collections import Counter
from pathlib import Path
from typing import Any, Optional

from src.retrieval.tokenize import tokenize


class BM25Index:
    def __init__(self, k1: float = 1.5, b: float = 0.75):
        self.k1 = k1
        self.b = b
        self.docs: list[str] = []
        self.doc_freqs: list[Counter] = []
        self.doc_lens: list[int] = []
        self.avgdl: float = 0.0
        self.idf: dict[str, float] = {}

    # ---------- 构建 ----------

    def add_documents(self, texts: list[str]) -> None:
        self.docs = list(texts)
        self.doc_freqs = [Counter(tokenize(t)) for t in self.docs]
        self.doc_lens = [sum(f.values()) for f in self.doc_freqs]
        self.avgdl = sum(self.doc_lens) / max(len(self.docs), 1)
        df: Counter = Counter()
        for freq in self.doc_freqs:
            for term in freq:
                df[term] += 1
        n = max(len(self.docs), 1)
        self.idf = {
            term: math.log(1 + (n - cnt + 0.5) / (cnt + 0.5))
            for term, cnt in df.items()
        }

    # ---------- 检索 ----------

    def search(self, query: str, top_k: int = 10) -> list[dict]:
        q_terms = tokenize(query)
        if not q_terms or not self.docs:
            return []
        scored: list[tuple[int, float]] = []
        for i in range(len(self.docs)):
            freq = self.doc_freqs[i]
            dl = self.doc_lens[i]
            score = 0.0
            for term in q_terms:
                tf = freq.get(term, 0)
                if tf == 0:
                    continue
                idf = self.idf.get(term, 0.0)
                denom = tf + self.k1 * (1 - self.b + self.b * dl / max(self.avgdl, 1e-6))
                score += idf * (tf * (self.k1 + 1)) / max(denom, 1e-9)
            if score > 0:
                scored.append((i, score))
        scored.sort(key=lambda x: x[1], reverse=True)
        return [
            {"index": i, "score": s, "text": self.docs[i]}
            for i, s in scored[:top_k]
        ]

    # ---------- 持久化 ----------

    def save(self, path: Any) -> None:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "k1": self.k1, "b": self.b, "docs": self.docs,
            "doc_freqs": [dict(f) for f in self.doc_freqs],
            "doc_lens": self.doc_lens, "avgdl": self.avgdl, "idf": self.idf,
        }
        path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")

    @classmethod
    def load(cls, path: Any) -> "BM25Index":
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        idx = cls(k1=data.get("k1", 1.5), b=data.get("b", 0.75))
        idx.docs = data["docs"]
        idx.doc_freqs = [Counter(d) for d in data.get("doc_freqs", [])]
        idx.doc_lens = data.get("doc_lens", [len(f) for f in idx.doc_freqs])
        idx.avgdl = data.get("avgdl", 0.0)
        idx.idf = data.get("idf", {})
        return idx
