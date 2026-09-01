"""W3 切块建库 —— parsed/ LayoutBlock → corpus/chunks.json

用法:
    python scripts/build_corpus.py
    python scripts/build_corpus.py --source data/parsed_demo --out data/corpus_demo
    python scripts/build_corpus.py --chunker fixed --chunk-size 500 --overlap 50   # A/B 对照
"""
from __future__ import annotations

import argparse
import json
import logging
import re
import sys
from collections import Counter
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("build_corpus")

from config.settings import CORPUS_DIR, PARSED_DIR  # noqa: E402
from src.chunking.chunker import build_chunks, save_chunks  # noqa: E402
from src.ingestion.layout import load_blocks  # noqa: E402

_YEAR_RE = re.compile(r"(20\d{2})年")  # 匹配"20xx年"（报告期），避免误取发布日期

# 股票代码 → 公司名（检索元数据用；文件名可能不含公司名，如平安"2023年年度报告.pdf"）
_COMPANY_NAMES = {
    "000001": "平安银行", "600519": "贵州茅台", "000002": "万科A", "600036": "招商银行",
    "600030": "中信证券", "601318": "中国平安", "300750": "宁德时代", "600276": "恒瑞医药",
    "000858": "五粮液", "601899": "紫金矿业",
}


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="切块建库：LayoutBlock → Chunk")
    p.add_argument("--source", default=str(PARSED_DIR), help="解析结果目录（*.json）")
    p.add_argument("--out", default=str(CORPUS_DIR / "chunks.json"), help="chunk 库输出路径")
    p.add_argument("--chunker", default="structural", choices=["structural", "fixed"],
                   help="structural=结构感知（默认），fixed=固定切块（对照）")
    p.add_argument("--chunk-size", type=int, default=600)
    p.add_argument("--overlap", type=int, default=80)
    p.add_argument("--max-table-rows", type=int, default=30)
    return p.parse_args()


def infer_doc_meta(doc_id: str) -> dict:
    """从 doc_id（相对路径，如 600519/ndbg/600519_2024-03-31_xxx.pdf.json）推断文档元数据"""
    meta = {"doc_id": doc_id, "title": Path(doc_id).stem, "company": "", "period_year": None}
    parts = doc_id.replace("\\", "/").split("/")
    if parts:
        code = parts[0]
        meta["company"] = _COMPANY_NAMES.get(code, code)
        m = _YEAR_RE.search(doc_id)
        if m:
            meta["period_year"] = int(m.group(1))
    return meta


def main() -> int:
    args = parse_args()
    source = Path(args.source)
    if not source.exists():
        logger.error("解析结果目录不存在: %s", source)
        return 2

    json_files = sorted(source.rglob("*.json"))
    if not json_files:
        logger.error("没有找到解析 JSON: %s", source)
        return 2

    blocks_by_doc: dict[str, list] = {}
    doc_meta: dict[str, dict] = {}
    for jf in json_files:
        rel = jf.relative_to(source)
        doc_id = str(rel.with_suffix("")).replace("\\", "/")
        try:
            blocks_by_doc[doc_id] = load_blocks(jf)
            doc_meta[doc_id] = infer_doc_meta(doc_id)
        except Exception as e:  # noqa: BLE001
            logger.warning("加载失败 %s: %s", jf, e)

    logger.info("切块中（%s, size=%d, overlap=%d）...", args.chunker, args.chunk_size, args.overlap)
    chunks = build_chunks(
        blocks_by_doc, doc_meta,
        chunker=args.chunker, chunk_size=args.chunk_size,
        overlap=args.overlap, max_table_rows=args.max_table_rows,
    )
    if not chunks:
        logger.error("切块结果为空")
        return 1

    save_chunks(chunks, args.out)
    by_type = Counter(c.block_type for c in chunks)
    by_year = Counter(c.period_year for c in chunks if c.period_year)
    logger.info(
        "完成: %d 个 chunk（类型 %s，年度 %s）→ %s",
        len(chunks), dict(by_type), dict(by_year), args.out,
    )
    # 摘要
    summary = Path(args.out).with_suffix(".summary.json")
    summary.write_text(
        json.dumps({
            "chunker": args.chunker, "chunk_size": args.chunk_size, "overlap": args.overlap,
            "total": len(chunks), "by_type": dict(by_type), "by_year": dict(by_year),
            "docs": len(blocks_by_doc),
        }, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
