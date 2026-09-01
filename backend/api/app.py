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
from fastapi.responses import HTMLResponse
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
                "source_name": h["chunk"].friendly_source(),
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
            {"score": h["score"], "source": h["chunk"].source, "source_name": h["chunk"].friendly_source(),
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


_INDEX_HTML = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Financial-RAG-Agent</title>
<style>
  body{font-family:"Microsoft YaHei",sans-serif;max-width:860px;margin:0 auto;padding:24px;background:#f7f8fa;color:#222}
  h1{font-size:22px} h2{font-size:16px;margin-top:24px}
  .card{background:#fff;border:1px solid #e3e6ea;border-radius:10px;padding:16px;margin-top:12px}
  input[type=text]{width:calc(100% - 90px);padding:10px;border:1px solid #ccc;border-radius:6px;font-size:14px}
  button{padding:10px 16px;border:none;border-radius:6px;background:#1677ff;color:#fff;font-size:14px;cursor:pointer;margin-left:8px}
  button:hover{background:#0958d9}
  pre{background:#f6f8fa;border-radius:6px;padding:12px;overflow:auto;font-size:13px;white-space:pre-wrap;word-break:break-all}
  .tag{display:inline-block;padding:2px 8px;border-radius:10px;background:#e6f4ff;color:#0958d9;font-size:12px;margin-right:6px}
  .ref{font-size:12px;color:#666;margin-top:8px}
  .err{color:#d4380d}
  a{color:#1677ff}
</style>
</head>
<body>
<h1>📈 Financial-RAG-Agent</h1>
<p>面向 A 股年报/公告的垂直金融 RAG 系统 · <a href="/docs">API 文档 (Swagger)</a></p>

<div class="card">
  <h2>Agent 问答</h2>
  <div>
    <input type="text" id="q" placeholder="例如：示例科技2023年的毛利率是多少？" onkeydown="if(event.key==='Enter')ask()">
    <button onclick="ask()">提问</button>
  </div>
  <pre id="chat-out">（输入问题后点"提问"）</pre>
</div>

<div class="card">
  <h2>检索</h2>
  <div>
    <input type="text" id="sq" placeholder="例如：示例科技2023年的营业收入" onkeydown="if(event.key==='Enter')search()">
    <button onclick="search()">检索</button>
  </div>
  <pre id="search-out">（输入查询后点"检索"）</pre>
</div>

<script>
async function post(url, body){
  const r = await fetch(url, {method:"POST", headers:{"Content-Type":"application/json"}, body:JSON.stringify(body)});
  if (!r.ok) { const e = await r.json().catch(()=>({})); throw new Error(e.detail || ("HTTP " + r.status)); }
  return r.json();
}
async function ask(){
  const q = document.getElementById("q").value.trim();
  const out = document.getElementById("chat-out");
  if(!q) return;
  out.textContent = "思考中…";
  try{
    const d = await post("/api/chat", {question:q, top_k:5});
    let s = "【意图】" + (d.intent||"") + (d.refused ? "（已拒答）" : "") + "\n\n" + d.answer;
    if(d.num_check && d.num_check.length) s += "\n\n⚠️ 数字校验未通过: " + d.num_check.join(", ");
    s += "\n\n--- 检索依据 ---";
    (d.hits||[]).forEach((h,i)=>{ s += "\n["+(i+1)+"] " + (h.source_name || h.source.split("\\").pop()) + " 第" + h.page + "页 (score " + h.score.toFixed(3) + ")"; });
    out.textContent = s;
  }catch(e){ out.textContent = "❌ " + e.message; }
}
async function search(){
  const q = document.getElementById("sq").value.trim();
  const out = document.getElementById("search-out");
  if(!q) return;
  out.textContent = "检索中…";
  try{
    const d = await post("/api/search", {question:q, top_k:5});
    let s = "";
    (d.hits||[]).forEach((h,i)=>{ s += "["+(i+1)+"] " + h.source.split("\\").pop() + " 第" + h.page + "页 (score " + h.score.toFixed(3) + ")\n    " + h.text.replace(/\n/g," ") + "\n\n"; });
    out.textContent = s || "（无结果）";
  }catch(e){ out.textContent = "❌ " + e.message; }
}
</script>
</body>
</html>"""


@app.get("/", response_class=HTMLResponse)
def index():
    """首页：简易演示界面"""
    return HTMLResponse(_INDEX_HTML)

@app.get("/api/eval/report")
def eval_report():
    """列出最近评估报告"""
    outdir = EVAL_REPORT_DIR
    if not outdir.exists():
        return {"reports": []}
    files = sorted(outdir.glob("*.md"), key=lambda p: p.stat().st_mtime, reverse=True)[:20]
    return {"reports": [{"name": f.name, "path": str(f)} for f in files]}


# ===== 知识库管理（上传/列表/删除，见 api/kb.py）=====
from api.kb import router as kb_router
app.include_router(kb_router)
