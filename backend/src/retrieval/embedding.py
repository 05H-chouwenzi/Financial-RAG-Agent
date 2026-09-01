"""Embedding —— 多后端：Dashscope API / 本地 bge / hash 占位

- dashscope: text-embedding-v3（推荐，需 API Key）
- bge: sentence-transformers 本地模型（需安装 torch + 模型）
- hash: 字符 n-gram 哈希袋（仅演示流程，无语义）
"""
from __future__ import annotations

import hashlib
import logging
from functools import lru_cache

import numpy as np

from config.settings import (
    DASHSCOPE_API_KEY,
    DASHSCOPE_BASE_URL,
    EMBEDDING_DIM,
    EMBEDDING_MODEL,
    EMBEDDING_PROVIDER,
)
from src.retrieval.tokenize import tokenize

logger = logging.getLogger("embedding")


def get_embedding_dim() -> int:
    return EMBEDDING_DIM


def _dashscope_embed(texts: list[str]) -> list[list[float]]:
    from openai import OpenAI

    client = OpenAI(
        api_key=DASHSCOPE_API_KEY,
        base_url=DASHSCOPE_BASE_URL,
        timeout=30.0,
        max_retries=1,
    )
    out: list[list[float]] = []
    BATCH = 10  # Dashscope text-embedding-v3 批量上限 10
    for i in range(0, len(texts), BATCH):
        batch = texts[i : i + BATCH]
        resp = client.embeddings.create(model=EMBEDDING_MODEL, input=batch)
        ordered = [None] * len(batch)
        for d in resp.data:
            ordered[d.index] = d.embedding
        out.extend(ordered)
    return out


@lru_cache(maxsize=1)
def _bge_model():
    from sentence_transformers import SentenceTransformer  # type: ignore

    logger.info("加载本地 embedding 模型: %s", EMBEDDING_MODEL)
    return SentenceTransformer(EMBEDDING_MODEL)


def _bge_embed(texts: list[str]) -> list[list[float]]:
    model = _bge_model()
    return model.encode(texts, normalize_embeddings=True).tolist()


def _hash_embed(texts: list[str]) -> list[list[float]]:
    """占位 embedding：字符 n-gram 哈希袋（无语义，仅供无 API 时演示流程）"""
    dim = EMBEDDING_DIM
    out = []
    for t in texts:
        vec = np.zeros(dim, dtype=np.float32)
        for tok in tokenize(t):
            h = int(hashlib.md5(tok.encode("utf-8")).hexdigest(), 16)
            vec[h % dim] += 1.0
        n = float(np.linalg.norm(vec))
        if n > 0:
            vec /= n
        out.append(vec.tolist())
    return out


def embed_texts(texts: list[str]) -> list[list[float]]:
    """统一入口：按配置选择后端，失败自动降级"""
    if not texts:
        return []
    provider = EMBEDDING_PROVIDER

    if provider == "dashscope":
        if not DASHSCOPE_API_KEY:
            logger.warning("未配置 DASHSCOPE_API_KEY，跳过 dashscope embedding")
        else:
            try:
                return _dashscope_embed(texts)
            except Exception as e:  # noqa: BLE001
                logger.warning("dashscope embedding 失败（%s），尝试本地模型", e)

    if provider in ("bge", "dashscope"):
        try:
            return _bge_embed(texts)
        except Exception as e:  # noqa: BLE001
            logger.debug("本地 bge 不可用（%s）", e)

    logger.warning("使用 hash 占位 embedding（无语义，仅演示流程）")
    return _hash_embed(texts)


@lru_cache(maxsize=4096)
def embed_one(text: str) -> list[float]:
    """单文本 embedding（带缓存，评估/检索循环会复用）"""
    return embed_texts([text])[0]
