"""金融问答 Agent —— 意图识别 → 检索/工具 → 生成 → 校验

意图类型：
- fact / table / compare / multi_doc：走 RAGGenerator
- calc：优先用检索到的数字 + 计算工具算指标
- reject：明确拒答（知识库外/预测类/未披露类）
"""
from __future__ import annotations

import logging
from typing import Optional

from src.agent.tools import calc_from_evidence, detect_metric
from src.generation.generator import RAGGenerator

logger = logging.getLogger("financial_agent")

# 拒答关键词：预测未来、股价、未披露、内部等
_REJECT_KW = [
    "预测", "未来股价", "股价会", "涨停", "跌停", "买入", "卖出", "推荐", "内幕",
    "未披露", "还没公布", "2025年计划", "明年业绩", "应该买", "能涨",
]

# 表格类关键词：优先命中表格块（配合检索表格加权）
_TABLE_KW = ["股东", "十大", "持股", "占比", "前十大", "表格"]


class FinancialAgent:
    def __init__(self, generator: RAGGenerator, llm=None):
        self.generator = generator
        self.llm = llm or generator.llm

    # ---------- 意图识别 ----------

    def classify(self, question: str) -> str:
        """关键词规则识别意图（可后续升级为 LLM 分类）"""
        for kw in _REJECT_KW:
            if kw in question:
                return "reject"
        if detect_metric(question):
            return "calc"
        if any(k in question for k in _TABLE_KW):
            return "table"
        if any(k in question for k in ("对比", "相比", "差异", "哪个高", "变化")):
            return "compare"
        return "fact"

    # ---------- 主入口 ----------

    def ask(self, question: str, top_k: Optional[int] = None, final_k: Optional[int] = None) -> dict:
        intent = self.classify(question)
        result: dict = {"question": question, "intent": intent, "answer": "", "refused": False, "hits": []}

        if intent == "reject":
            result["refused"] = True
            result["answer"] = (
                "这个问题超出知识库范围（涉及预测/投资建议/未披露信息）。"
                "我只能基于已披露的年报与公告回答事实性问题。"
            )
            return result

        if intent == "calc":
            return self._answer_calc(question, result, top_k, final_k)

        gen = self.generator.answer(question, top_k=top_k, final_k=final_k)
        result.update(gen)
        return result

    # ---------- 计算类 ----------

    def _answer_calc(self, question: str, result: dict, top_k, final_k) -> dict:
        metric = detect_metric(question) or ""
        hits = self.generator.retriever.retrieve(question, top_k=top_k, final_k=max(final_k or 3, 3))
        result["hits"] = hits
        if not hits:
            result["refused"] = True
            result["answer"] = "知识库中没有找到计算所需的财务数据。"
            return result

        evidence_text = "\n".join(h["text"] for h in hits[:3])
        calc = calc_from_evidence(metric, evidence_text)
        if calc is None:
            # 提取失败 → 退回普通 RAG 回答
            gen = self.generator.answer(question, top_k=top_k, final_k=final_k)
            result.update(gen)
            result["answer"] = (
                "未能从证据中自动提取计算字段，以下为检索结果：\n\n" + gen["answer"]
            )
            return result

        value = calc["value"]
        unit = "元"
        # 尝试带单位输出
        if metric == "debt_ratio":
            result["answer"] = f"根据检索到的数据计算，资产负债率 = {value:.2%}。"
        elif metric in ("gross_margin", "net_margin"):
            result["answer"] = f"根据检索到的数据计算，{_metric_name(metric)} = {value:.2%}。"
        else:
            result["answer"] = f"根据检索到的数据计算，{_metric_name(metric)} = {value:.4f}（字段: {calc['fields']}）。"
        result["answer"] += "\n\n（注：数值由检索证据自动提取计算，请以原始报告披露为准。）"
        result["calc"] = calc
        return result


def _metric_name(metric: str) -> str:
    return {
        "roe": "净资产收益率(ROE)", "gross_margin": "毛利率",
        "net_margin": "净利率", "debt_ratio": "资产负债率", "growth": "同比增长率",
    }.get(metric, metric)
