"""评估 Runner —— 检索评估 + 生成评估，统一入口"""
from __future__ import annotations

import logging
import re
from typing import Optional

from src.eval.golden_set import GoldenItem
from src.eval.metrics import summarize_retrieval
from src.eval.ragas_eval import ragas_evaluate
from src.generation.generator import RAGGenerator

logger = logging.getLogger("eval_runner")


def _norm(text: str) -> str:
    """归一化：去掉所有空白，便于证据匹配"""
    return re.sub(r"\s+", "", text or "")


_NUM_RE = re.compile(r"\d+(?:,\d{3})*(?:\.\d+)?")


def _extract_nums(text: str) -> set[str]:
    """提取数字（去逗号、排除年份 20xx），用于相关性判定"""
    out = set()
    for m in _NUM_RE.findall(text or ""):
        num = m.replace(",", "")
        if re.fullmatch(r"20\d{2}", num):
            continue  # 年份过于宽泛，不参与匹配
        if len(num) >= 3:
            out.add(num)
    return out


def compute_relevant(chunks: list, item: GoldenItem) -> set[int]:
    """计算 golden item 的相关 chunk index 集合

    匹配逻辑（由严到宽）：
    1. doc_id 命中 且 证据片段命中（归一化子串）
    2. doc_id 命中 且 与证据共享至少一个关键数字（表格等异形同值块也算相关）
    3. 都为空时退化为文档级匹配
    """
    expected = {x.strip() for x in item.doc_ids.split(";") if x.strip()}
    ev = _norm(item.evidence)
    ev_nums = _extract_nums(item.evidence)
    relevant: set[int] = set()
    for i, c in enumerate(chunks):
        if expected and c.doc_id not in expected:
            continue
        if ev and ev in _norm(c.text):
            relevant.add(i)
            continue
        if ev_nums and (_extract_nums(c.text) & ev_nums):
            relevant.add(i)
    if not relevant and expected:
        relevant = {i for i, c in enumerate(chunks) if c.doc_id in expected}
    return relevant


class EvalRunner:
    def __init__(self, retriever, golden_items: list[GoldenItem]):
        self.retriever = retriever
        self.golden_items = golden_items
        self.chunks = retriever.chunks

    # ---------- 检索评估 ----------

    def run_retrieval(self, top_ks=(3, 5, 10)) -> tuple[dict, list[dict]]:
        """对每个 golden item 检索，返回 (汇总指标, 逐条结果)"""
        ranked_lists: list[list[int]] = []
        relevant_sets: list[set[int]] = []
        per_query: list[dict] = []

        for it in self.golden_items:
            if it.type == "reject":
                # 拒答样本不参与检索评估（检索相关性无意义）
                continue
            hits = self.retriever.retrieve(it.question)
            ranked = [h["index"] for h in hits]
            relevant = compute_relevant(self.chunks, it)
            ranked_lists.append(ranked)
            relevant_sets.append(relevant)
            per_query.append({
                "question": it.question, "type": it.type,
                "hit5": 1.0 if any(i in relevant for i in ranked[:5]) else 0.0,
                "mrr": _mrr(ranked, relevant),
            })

        metrics = summarize_retrieval(ranked_lists, relevant_sets, top_ks=top_ks)
        return metrics, per_query

    # ---------- 生成评估 ----------

    def run_generation(
        self,
        generator: RAGGenerator,
        use_ragas: bool = False,
        agent=None,
    ) -> tuple[dict, list[dict]]:
        """对每个 non-reject golden item 生成回答，统计质量"""
        questions: list[str] = []
        answers: list[str] = []
        contexts: list[list[str]] = []
        truths: list[str] = []
        per_query: list[dict] = []
        n_refused = 0
        n_refused_ok = 0
        n_num_ok = 0
        n_total = 0

        for it in self.golden_items:
            if it.type == "reject":
                # 拒答样本：期望被拒（走 Agent 意图分类，而非普通检索）
                res = agent.ask(it.question) if agent is not None else generator.answer(it.question)
                refused = res["refused"]
                n_refused += 1
                n_refused_ok += 1 if refused else 0
                per_query.append({
                    "question": it.question, "type": it.type,
                    "refused": refused, "num_check": [], "answer": res["answer"][:120],
                })
                continue

            res = generator.answer(it.question)
            n_total += 1
            if not res["num_check"]:
                n_num_ok += 1
            questions.append(it.question)
            answers.append(res["answer"])
            contexts.append([h["text"] for h in res["hits"]])
            truths.append(it.answer)
            per_query.append({
                "question": it.question, "type": it.type,
                "refused": res["refused"], "num_check": res["num_check"],
                "answer": res["answer"][:120],
            })

        stats: dict = {
            "n": n_total,
            "refused_samples": n_refused,
            "refusal_accuracy": n_refused_ok / n_refused if n_refused else None,
            "number_check_pass_rate": n_num_ok / n_total if n_total else None,
        }

        if use_ragas and questions:
            ragas = ragas_evaluate(questions, answers, contexts, truths)
            stats["ragas"] = ragas
        return stats, per_query


def _mrr(ranked: list[int], relevant: set[int]) -> float:
    for rank, i in enumerate(ranked, 1):
        if i in relevant:
            return 1.0 / rank
    return 0.0
