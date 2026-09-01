"""稠密向量检索 —— FAISS（IndexFlatIP）优先，numpy 暴力余弦兜底

持久化：vectors.npy + texts.json + metas.json，加载时重建 FAISS 索引。
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Optional

import numpy as np

from src.retrieval.embedding import embed_texts, get_embedding_dim


class DenseIndex:
    def __init__(self, dim: Optional[int] = None):
        self.dim = dim or get_embedding_dim()
        self.texts: list[str] = []
        self.metas: list[dict] = []
        self.vectors = np.zeros((0, self.dim), dtype=np.float32)
        self._faiss_index = None
        try:
            import faiss  # type: ignore

            self._faiss_ok = True
        except Exception:  # noqa: BLE001
            self._faiss_ok = False

    # ---------- 构建 ----------

    def add(self, texts: list[str], metas: Optional[list[dict]] = None) -> None:
        if not texts:
            return
        vecs = np.asarray(embed_texts(texts), dtype=np.float32).reshape(len(texts), self.dim)
        self._normalize_inplace(vecs)
        self.vectors = np.vstack([self.vectors, vecs]) if self.vectors.size else vecs
        self.texts.extend(texts)
        self.metas.extend(metas or [{}] * len(texts))
        self._rebuild_faiss()

    def _normalize_inplace(self, arr: np.ndarray) -> None:
        norms = np.linalg.norm(arr, axis=1, keepdims=True)
        arr /= np.clip(norms, 1e-8, None)

    def _rebuild_faiss(self) -> None:
        if not self._faiss_ok or self.vectors.size == 0:
            return
        try:
            import faiss  # type: ignore

            idx = faiss.IndexFlatIP(self.dim)
            idx.add(self.vectors)
            self._faiss_index = idx
        except Exception:  # noqa: BLE001
            self._faiss_index = None

    # ---------- 检索 ----------

    def search(self, query_vec: list[float], top_k: int = 10) -> list[dict]:
        if self.vectors.size == 0:
            return []
        q = np.asarray([query_vec], dtype=np.float32).reshape(1, self.dim)
        self._normalize_inplace(q)
        k = min(top_k, len(self.texts))

        if self._faiss_index is not None and self._faiss_index.ntotal > 0:
            scores, idxs = self._faiss_index.search(q, k)
            scores = scores[0]
            idxs = idxs[0]
        else:
            scores = (self.vectors @ q[0]).flatten()
            idxs = np.argsort(-scores)[:k]
            scores = scores[idxs]

        out = []
        for i, s in zip(idxs, scores):
            i = int(i)
            if i < 0 or i >= len(self.texts):
                continue
            out.append({"index": i, "score": float(s), "text": self.texts[i], "meta": self.metas[i]})
        return out

    # ---------- 持久化 ----------

    def save(self, path: Any) -> None:
        path = Path(path)
        path.mkdir(parents=True, exist_ok=True)
        np.save(path / "vectors.npy", self.vectors)
        (path / "texts.json").write_text(
            json.dumps(self.texts, ensure_ascii=False), encoding="utf-8"
        )
        (path / "metas.json").write_text(
            json.dumps(self.metas, ensure_ascii=False), encoding="utf-8"
        )

    @classmethod
    def load(cls, path: Any) -> "DenseIndex":
        path = Path(path)
        idx = cls(dim=int(get_embedding_dim()))
        idx.vectors = np.load(path / "vectors.npy")
        idx.texts = json.loads((path / "texts.json").read_text(encoding="utf-8"))
        idx.metas = json.loads((path / "metas.json").read_text(encoding="utf-8"))
        idx._rebuild_faiss()
        return idx
