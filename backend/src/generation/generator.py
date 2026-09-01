"""RAG 生成器 —— 检索 → 组装 Prompt → LLM → 数字校验 → 引用溯源 → 拒答

对应规划 M5 的三个安全机制：
1. 引用溯源：ensure_citations
2. 数字校验：check_numbers
3. 拒答：should_refuse
"""
from __future__ import annotations

import logging
from typing import Optional

from config.settings import REFUSAL_THRESHOLD, STRICT_NUMBERS
from src.generation.checks import check_numbers, ensure_citations, should_refuse
from src.generation.llm import LLMClient

logger = logging.getLogger("generator")

SYSTEM_PROMPT = (
    "你是专业的金融分析师助手。请基于提供的【参考资料】回答问题，"
    "做到：1) 只依据资料内容，不编造；2) 涉及数字时保持精确；"
    "3) 回答中按 [1][2] 标注引用来源；4) 资料不足以回答时明确说明。"
)


class RAGGenerator:
    def __init__(
        self,
        retriever,
        llm: Optional[LLMClient] = None,
        refusal_threshold: float = REFUSAL_THRESHOLD,
        strict_numbers: bool = STRICT_NUMBERS,
    ):
        self.retriever = retriever
        self.llm = llm or LLMClient()
        self.refusal_threshold = refusal_threshold
        self.strict_numbers = strict_numbers

    def _build_prompt(self, query: str, hits: list[dict]) -> str:
        parts = [f"问题：{query}", "", "【参考资料】"]
        for i, h in enumerate(hits, 1):
            chunk = h["chunk"]
            parts.append(f"\n[{i}] 来源: {chunk.source} 第{chunk.page}页 章节: {chunk.section_path}")
            parts.append(h["text"][:1500])
        return "\n".join(parts)

    def answer(self, query: str, top_k: Optional[int] = None, final_k: Optional[int] = None) -> dict:
        """生成回答。返回 {answer, refused, hits, num_check, raw}"""
        hits = self.retriever.retrieve(query, top_k=top_k, final_k=final_k)
        result: dict = {"answer": "", "refused": False, "hits": hits, "num_check": []}

        if not hits:
            result["refused"] = True
            result["answer"] = "知识库中没有找到与问题相关的资料。"
            return result

        top_score = hits[0]["score"]
        if should_refuse(top_score, self.refusal_threshold):
            result["refused"] = True
            result["answer"] = (
                f"抱歉，知识库中未找到足够相关的资料（最高相关度 {top_score:.3f}，"
                "低于回答阈值）。请确认问题是否在知识库范围内。"
            )
            return result

        prompt = self._build_prompt(query, hits)
        raw = self.llm.chat([
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ])
        answer = raw

        # 数字校验
        if self.strict_numbers:
            evidences = [{"text": h["text"], "chunk": h["chunk"]} for h in hits]
            missing = check_numbers(answer, evidences)
            result["num_check"] = missing
            if missing:
                answer += (
                    "\n\n⚠️ 数字核验提示：回答中的数字 "
                    f"{missing} 未在检索证据中直接找到，请以原始报告为准。"
                )

        # 引用溯源
        answer = ensure_citations(answer, [{"text": h["text"], "chunk": h["chunk"]} for h in hits])
        result["answer"] = answer
        return result
