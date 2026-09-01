"""RAGAS 评估（可选）—— 需要安装 ragas 并配置 LLM

如果 ragas 未安装或调用失败，返回 {"error": ...}，不影响主流程。
LLM 复用项目 .env 的 OpenAI 兼容配置（DeepSeek / Dashscope），无需额外环境变量。
"""
from __future__ import annotations

import logging
from typing import Optional

logger = logging.getLogger("ragas_eval")


def _ragas_llm():
    """用项目配置（DASHSCOPE_BASE_URL / DASHSCOPE_API_KEY / LLM_MODEL）构造 RAGAS 的 LLM"""
    from config.settings import DASHSCOPE_API_KEY, DASHSCOPE_BASE_URL, LLM_MODEL

    if not DASHSCOPE_API_KEY:
        return None
    # ragas 0.4.x：用 LangchainLLMWrapper 包一个 OpenAI 兼容 client（DeepSeek 等）
    from langchain_openai import ChatOpenAI

    from ragas.llms import LangchainLLMWrapper  # type: ignore

    chat = ChatOpenAI(
        model=LLM_MODEL,
        base_url=DASHSCOPE_BASE_URL,
        api_key=DASHSCOPE_API_KEY,
        temperature=0,
    )
    return LangchainLLMWrapper(chat)


def _ragas_embeddings():
    """用项目本地 bge 向量模型作为 RAGAS 的 embeddings。

    ResponseRelevancy 需要 embeddings（embed_query/embed_documents 的 langchain 接口）计算
    问题-回答相似度；DeepSeek 没有 embeddings 接口，所以复用本地 bge-small-zh-v1.5
    （与检索同模型，512 维），用 LangchainEmbeddingsWrapper 包一层。
    """
    from config.settings import EMBEDDING_MODEL

    try:
        from langchain_community.embeddings import HuggingFaceEmbeddings  # type: ignore

        from ragas.embeddings import LangchainEmbeddingsWrapper  # type: ignore

        return LangchainEmbeddingsWrapper(HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL))
    except Exception as e:  # noqa: BLE001
        logger.warning("RAGAS 本地 embeddings 初始化失败（%s）", e)
        return None


def ragas_evaluate(
    questions: list[str],
    answers: list[str],
    contexts: list[list[str]],
    ground_truths: list[str],
    llm: Optional[object] = None,
) -> dict:
    """RAGAS 生成质量评估（faithfulness / answer_relevancy / context_precision / context_recall）"""
    try:
        from ragas import EvaluationDataset, SingleTurnSample, evaluate  # type: ignore
        try:  # ragas >= 0.4 推荐路径；老版本回退
            from ragas.metrics.collections import (  # type: ignore
                Faithfulness,
                LLMContextPrecisionWithoutReference,
                LLMContextRecall,
                ResponseRelevancy,
            )
        except Exception:  # noqa: BLE001
            from ragas.metrics import (  # type: ignore
                LLMContextPrecisionWithoutReference,
                LLMContextRecall,
                ResponseRelevancy,
                Faithfulness,
            )
    except Exception as e:  # noqa: BLE001
        return {"error": f"ragas 未安装或导入失败: {e}"}

    try:
        if llm is None:
            llm = _ragas_llm()
        embeddings = _ragas_embeddings()
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
        from ragas.run_config import RunConfig  # type: ignore

        # DeepSeek 并发响应慢：调大单任务超时并降低并发，避免 context_precision 等长链指标超时
        result = evaluate(
            dataset,
            metrics=[
                Faithfulness(),
                # DeepSeek 等兼容接口只支持 n=1：strictness 默认 2 会发 n=2 报 400
                ResponseRelevancy(strictness=1),
                LLMContextPrecisionWithoutReference(),
                LLMContextRecall(),
            ],
            llm=llm,
            embeddings=embeddings,
            run_config=RunConfig(timeout=600, max_retries=2, max_workers=4),
        )
        return result.to_pandas().to_dict(orient="list")
    except Exception as e:  # noqa: BLE001
        return {"error": f"RAGAS 评估失败: {e}"}
