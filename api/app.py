"""Financial-RAG-Agent API —— FastAPI 服务

端点：
- GET  /api/health            健康检查
- POST /api/search            检索（返回命中片段）
- POST /api/chat              金融 Agent 问答
- GET  /api/intent            意图识别
- GET  /api/eval/report       最近评估报告列表

启动：python scripts/serve_api.py  （或 uvicorn api.app:app）
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from config.settings import CORPUS_DIR, EVAL_REPORT_DIR, INDEX_DIR

logger = logging.getLogger("api")

app = FastAPI(title="Financial-RAG-Agent", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# 延迟加载的检索器/Agent（首次请求时初始化）
_retriever = None
_agent = None
_load_error: Optional[str] = None


def _ensure_loaded():
    global _retriever, _agent, _load_error
    if _retriever is not None or _load_error is not None:
        return
    try:
        from src.agent.financial_agent import FinancialAgent
        from src.generation.generator import RAGGenerator
        from src.retrieval.retriever import load_index

        chunk_path = CORPUS_DIR / "chunks.json"
        if not INDEX_DIR.exists() or not chunk_path.exists():
            _load_error = (
                f"索引未构建：{INDEX_DIR} 或 {chunk_path} 不存在。"
                "请先运行 scripts/parse_documents.py → build_corpus.py → index_corpus.py"
            )
            logger.warning(_load_error)
            return
        retriever = load_index(INDEX_DIR, chunk_path)
        generator = RAGGenerator(retriever)
        agent = FinancialAgent(generator)
        _retriever, _agent = retriever, agent
    except Exception as e:  # noqa: BLE001
        _load_error = f"初始化失败: {e}"
        logger.exception("API 初始化失败")


class SearchRequest(BaseModel):
    question: str = Field(..., min_length=1, description="查询问题")
    top_k: int = Field(5, ge=1, le=20)


class ChatRequest(BaseModel):
    question: str = Field(..., min_length=1, description="用户问题")
    top_k: int = Field(5, ge=1, le=20)


@app.get("/api/health")
def health():
    _ensure_loaded()
    return {
        "status": "ok" if _retriever is not None else "not_ready",
        "error": _load_error,
    }


@app.post("/api/search")
def search(req: SearchRequest):
    _ensure_loaded()
    if _retriever is None:
        raise HTTPException(503, _load_error or "未就绪")
    hits = _retriever.retrieve(req.question, final_k=req.top_k)
    return {
        "question": req.question,
        "hits": [
            {
                "score": h["score"],
                "source": h["chunk"].source,
                "page": h["chunk"].page,
                "section": h["chunk"].section_path,
                "year": h["chunk"].period_year,
                "text": h["text"][:600],
            }
            for h in hits
        ],
    }


@app.post("/api/chat")
def chat(req: ChatRequest):
    _ensure_loaded()
    if _agent is None:
        raise HTTPException(503, _load_error or "未就绪")
    result = _agent.ask(req.question, final_k=req.top_k)
    return {
        "question": result["question"],
        "intent": result.get("intent"),
        "answer": result["answer"],
        "refused": result.get("refused", False),
        "num_check": result.get("num_check", []),
        "hits": [
            {"score": h["score"], "source": h["chunk"].source,
             "page": h["chunk"].page, "text": h["text"][:300]}
            for h in result.get("hits", [])
        ],
    }


@app.get("/api/intent")
def intent(question: str):
    _ensure_loaded()
    if _agent is None:
        raise HTTPException(503, _load_error or "未就绪")
    return {"question": question, "intent": _agent.classify(question)}


@app.get("/api/eval/report")
def eval_report():
    """列出最近评估报告"""
    outdir = EVAL_REPORT_DIR
    if not outdir.exists():
        return {"reports": []}
    files = sorted(outdir.glob("*.md"), key=lambda p: p.stat().st_mtime, reverse=True)[:20]
    return {"reports": [{"name": f.name, "path": str(f)} for f in files]}
