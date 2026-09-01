"""重排 —— bge-reranker（FlagEmbedding）优先，词法重排兜底

bge-reranker 是交叉编码器（query,doc 一起编码打分），比双塔向量更准但更慢，
所以只对融合后的 top-N 候选重排。
"""
from __future__ import annotations

import logging
from typing import Optional

from config.settings import RERANK_MODEL
from src.retrieval.tokenize import tokenize

logger = logging.getLogger("rerank")


class Reranker:
    def __init__(self, model_name: Optional[str] = None):
        self.model_name = model_name or RERANK_MODEL
        self._model = None
        self.backend = self._detect()

    def _detect(self) -> str:
        try:
            from FlagEmbedding import FlagReranker  # noqa: F401

            return "bge"
        except Exception:  # noqa: BLE001
            logger.warning("FlagEmbedding 未安装，重排使用词法兜底")
            return "lexical"

    def _load(self):
        if self._model is None and self.backend == "bge":
            try:
                from FlagEmbedding import FlagReranker  # type: ignore

                self._model = FlagReranker(self.model_name, use_fp16=False)
            except Exception as e:  # noqa: BLE001
                logger.warning("bge-reranker 加载失败（%s），切换词法兜底", e)
                self.backend = "lexical"

    def rerank(self, query: str, hits: list[dict], top_k: int = 5) -> list[dict]:
        """对 hits 重排，返回前 top_k"""
        if not hits:
            return []
        if len(hits) <= 1:
            return hits[:top_k]
        self._load()
        if self.backend == "bge":
            try:
                pairs = [(query, h["text"]) for h in hits]
                scores = self._model.compute_score(pairs, normalize=True)
                for h, s in zip(hits, scores):
                    h["score"] = float(s)
                hits.sort(key=lambda h: h["score"], reverse=True)
                return hits[:top_k]
            except Exception as e:  # noqa: BLE001
                logger.warning("bge-reranker 打分失败（%s），切换词法兜底", e)
                self.backend = "lexical"

        # 词法兜底：query 与 doc 的 token 重叠率 + 保留原分
        # 用 search_text（含公司/年份/章节元数据）计算重叠，
        # 否则"主要会计数据"等表格块原文不含公司名/年份，词法重叠被严重低估。
        q_tokens = set(tokenize(query))
        for h in hits:
            chunk = h.get("chunk")
            doc_text = chunk.search_text() if chunk is not None else h["text"]
            d_tokens = set(tokenize(doc_text))
            overlap = len(q_tokens & d_tokens) / max(len(q_tokens), 1)
            h["score"] = 0.5 * h["score"] + 0.5 * overlap
        hits.sort(key=lambda h: h["score"], reverse=True)
        return hits[:top_k]
