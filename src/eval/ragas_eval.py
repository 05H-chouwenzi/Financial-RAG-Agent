"""RAGAS 评估（可选）—— 需要安装 ragas 并配置 LLM

如果 ragas 未安装或调用失败，返回 {"error": ...}，不影响主流程。
"""
from __future__ import annotations

import logging

logger = logging.getLogger("ragas_eval")


def ragas_evaluate(
    questions: list[str],
    answers: list[str],
    contexts: list[list[str]],
    ground_truths: list[str],
) -> dict:
    """RAGAS 生成质量评估（faithfulness / answer_relevancy / context_precision / context_recall）"""
    try:
        from ragas import EvaluationDataset, SingleTurnSample, evaluate  # type: ignore
        from ragas.metrics import (  # type: ignore
            LLMContextPrecisionWithoutReference,
            LLMContextRecall,
            ResponseRelevancy,
            Faithfulness,
        )
    except Exception as e:  # noqa: BLE001
        return {"error": f"ragas 未安装或导入失败: {e}"}

    try:
        samples = [
            SingleTurnSample(
                user_input=q,
                response=a,
                retrieved_contexts=ctx,
                reference=g,
            )
            for q, a, ctx, g in zip(questions, answers, contexts, ground_truths)
        ]
        dataset = EvaluationDataset(samples=samples)
        result = evaluate(
            dataset,
            metrics=[
                Faithfulness(),
                ResponseRelevancy(),
                LLMContextPrecisionWithoutReference(),
                LLMContextRecall(),
            ],
        )
        return result.to_pandas().to_dict(orient="list")
    except Exception as e:  # noqa: BLE001
        return {"error": f"RAGAS 评估失败: {e}"}
