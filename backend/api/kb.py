"""知识库管理 API —— 上传/列表/删除 + 语料重建

前端知识库从"内存模拟上传"升级为真实链路：
上传 PDF → data/raw → 后台重建(解析→切块→索引) → 列表实时来自语料。
"""
from __future__ import annotations

import logging
import re
import subprocess
import sys
import threading
import time
from pathlib import Path

from fastapi import APIRouter, HTTPException, UploadFile
from fastapi.responses import FileResponse

from config.settings import BASE_DIR, CORPUS_DIR, INDEX_DIR, PARSED_DIR, RAW_DIR

logger = logging.getLogger("api.kb")

router = APIRouter(prefix="/api/knowledge", tags=["knowledge"])

UPLOAD_DIR = RAW_DIR / "upload"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

_COMPANY_NAMES = {
    "000001": "平安银行", "600519": "贵州茅台", "000002": "万科A", "600036": "招商银行",
    "600030": "中信证券", "601318": "中国平安", "300750": "宁德时代", "600276": "恒瑞医药",
    "000858": "五粮液", "601899": "紫金矿业",
}

_rebuild_lock = threading.Lock()
_rebuild_state = {"running": False, "last": None, "error": None}


def _friendly_name(stem: str) -> str:
    """文件名 → 可读名称：'000001_2024-03-15_2023年年度报告' → '平安银行 2023年年度报告'"""
    m = re.match(r"^(\d{6})_\d{4}-\d{2}-\d{2}_(.+)$", stem)
    if m:
        code, rest = m.group(1), m.group(2)
        company = _COMPANY_NAMES.get(code, "")
        if company and rest.startswith(company):
            return rest
        return f"{company} {rest}".strip() if company else rest
    return re.sub(r"^\d{4}-\d{2}-\d{2}_", "", stem)


def _scan_files() -> list[dict]:
    """扫描 data/raw 下所有 PDF，返回知识库列表"""
    out = []
    if not RAW_DIR.exists():
        return out
    for f in sorted(RAW_DIR.rglob("*.pdf")):
        rel = str(f.relative_to(RAW_DIR)).replace("\\", "/")
        size_kb = round(f.stat().st_size / 1024, 1)
        mtime_s = f.stat().st_mtime
        out.append({
            "id": f"kb-{rel}",
            "name": _friendly_name(f.stem),
            "kind": "pdf",
            "folder": "standard",
            "sizeKB": size_kb,
            "modifiedTs": int(mtime_s * 1000),
            "modifiedLabel": time.strftime("%Y/%m/%d", time.localtime(mtime_s)),
            "fileName": f"api/knowledge/file/{rel}",
            "backend": True,
        })
    return out


def _rebuild_worker():
    """后台重建语料：解析 → 切块 → 建索引 → 热更新检索器"""
    global _rebuild_state
    try:
        steps = [
            ("parse", [sys.executable, "scripts/parse_documents.py"]),
            ("corpus", [sys.executable, "scripts/build_corpus.py"]),
            ("index", [sys.executable, "scripts/index_corpus.py"]),
        ]
        for name, cmd in steps:
            r = subprocess.run(cmd, cwd=str(BASE_DIR), capture_output=True, text=True)
            if r.returncode != 0:
                _rebuild_state["error"] = f"{name} 失败: {r.stderr[-500:]}"
                logger.error(_rebuild_state["error"])
                return
        # 热更新全局检索器/Agent
        from src.agent.financial_agent import FinancialAgent
        from src.generation.generator import RAGGenerator
        from src.retrieval.retriever import load_index

        retriever = load_index(INDEX_DIR, CORPUS_DIR / "chunks.json")
        generator = RAGGenerator(retriever)
        agent = FinancialAgent(generator)
        import api.app as appmod

        appmod._retriever, appmod._agent, appmod._load_error = retriever, agent, None
        _rebuild_state["last"] = time.strftime("%Y-%m-%d %H:%M:%S")
        _rebuild_state["error"] = None
    finally:
        with _rebuild_lock:
            _rebuild_state["running"] = False


def _start_rebuild() -> None:
    with _rebuild_lock:
        if _rebuild_state["running"]:
            return
        _rebuild_state["running"] = True
    threading.Thread(target=_rebuild_worker, daemon=True).start()


@router.get("/files")
def list_files():
    return {"files": _scan_files(), "rebuilding": _rebuild_state["running"], "last": _rebuild_state["last"]}


@router.post("/upload")
async def upload(file: UploadFile):
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(400, "仅支持 PDF 文件")
    name = Path(file.filename).name
    # 重名去重
    dest = UPLOAD_DIR / name
    if dest.exists():
        dest = UPLOAD_DIR / f"{Path(name).stem}_{int(time.time())}.pdf"
    dest.parent.mkdir(parents=True, exist_ok=True)
    content = await file.read()
    dest.write_bytes(content)
    logger.info("上传 PDF → %s (%d bytes)", dest, len(content))
    _start_rebuild()
    return {
        "ok": True,
        "name": _friendly_name(dest.stem),
        "fileName": f"api/knowledge/file/upload/{dest.name}",
        "rebuilding": True,
        "message": "已上传，正在重建索引（几分钟内生效）",
    }


@router.get("/file/{path:path}")
def get_file(path: str):
    """返回语料 PDF（供前端预览/下载），限制在 RAW_DIR 内防穿越"""
    target = (RAW_DIR / path).resolve()
    if not str(target).startswith(str(RAW_DIR.resolve())) or not target.is_file():
        raise HTTPException(404, "文件不存在")
    return FileResponse(target, media_type="application/pdf", filename=target.name)


@router.delete("/files")
def delete_file(file: str):
    target = (RAW_DIR / file).resolve()
    if not str(target).startswith(str(RAW_DIR.resolve())) or not target.is_file():
        raise HTTPException(404, "文件不存在")
    target.unlink()
    logger.info("删除 PDF → %s", target)
    _start_rebuild()
    return {"ok": True, "message": "已删除，正在重建索引"}
