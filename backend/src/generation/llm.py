"""LLM 客户端 —— OpenAI 兼容接口（默认阿里云 Dashscope），无 Key 时占位兜底

所有调用失败都会降级：返回占位回答（带明确标记），保证全链路可跑通。
"""
from __future__ import annotations

import logging
from typing import Optional

from config.settings import (
    DASHSCOPE_API_KEY,
    DASHSCOPE_BASE_URL,
    LLM_MAX_TOKENS,
    LLM_MODEL,
    LLM_TEMPERATURE,
)

logger = logging.getLogger("llm")

_PLACEHOLDER_PREFIX = "【占位回答·未配置LLM】"


class LLMClient:
    def __init__(
        self,
        model: Optional[str] = None,
        temperature: float = LLM_TEMPERATURE,
        max_tokens: int = LLM_MAX_TOKENS,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
    ):
        self.model = model or LLM_MODEL
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.api_key = api_key if api_key is not None else DASHSCOPE_API_KEY
        self.base_url = base_url or DASHSCOPE_BASE_URL
        self._client = None

    @property
    def available(self) -> bool:
        return bool(self.api_key)

    def _get_client(self):
        if self._client is None:
            from openai import OpenAI

            self._client = OpenAI(api_key=self.api_key, base_url=self.base_url)
        return self._client

    def chat(self, messages: list[dict], **kw) -> str:
        """标准对话补全；失败返回占位回答"""
        if not self.available:
            logger.debug("未配置 LLM API Key，返回占位回答")
            return _placeholder_reply(messages)
        try:
            client = self._get_client()
            resp = client.chat.completions.create(
                model=kw.get("model", self.model),
                messages=messages,
                temperature=kw.get("temperature", self.temperature),
                max_tokens=kw.get("max_tokens", self.max_tokens),
            )
            return resp.choices[0].message.content or ""
        except Exception as e:  # noqa: BLE001
            logger.warning("LLM 调用失败（%s），返回占位回答", e)
            return _placeholder_reply(messages)


def _placeholder_reply(messages: list[dict]) -> str:
    """无 LLM 时的兜底：尽量返回用户问题的原文 + 标记"""
    for m in reversed(messages):
        if m.get("role") == "user":
            content = m.get("content", "")
            if isinstance(content, list):
                content = " ".join(str(x.get("text", "")) for x in content if isinstance(x, dict))
            return f"{_PLACEHOLDER_PREFIX} 请配置 DASHSCOPE_API_KEY 以获得真实回答。\n问题原文：{content}"
    return f"{_PLACEHOLDER_PREFIX} 请配置 DASHSCOPE_API_KEY 以获得真实回答。"
