"""W4 建索引 —— corpus/chunks.json → data/index（稠密向量 + BM25）

用法:
    python scripts/index_corpus.py
    python scripts/index_corpus.py --chunks data/corpus_demo/chunks.json --index data/index_demo
    python scripts/index_corpus.py --fusion rrf --no-rerank
"""
from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("index_corpus")

from config.settings import CORPUS_DIR, INDEX_DIR  # noqa: E402
from src.chunking.chunker import load_chunks  # noqa: E402
from src.retrieval.retriever import RetrievalConfig, Retriever, save_index  # noqa: E402


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="构建稠密+稀疏索引")
    p.add_argument("--chunks", default=str(CORPUS_DIR / "chunks.json"), help="chunk 库路径")
    p.add_argument("--index", default=str(INDEX_DIR), help="索引输出目录")
    p.add_argument("--fusion", default="rrf", choices=["weighted", "rrf"])
    p.add_argument("--no-rerank", action="store_true", help="关闭重排")
    p.add_argument("--no-time-filter", action="store_true", help="关闭时间过滤")
    p.add_argument("--no-table-weight", action="store_true", help="关闭表格加权")
    return p.parse_args()


def main() -> int:
    args = parse_args()
    chunk_path = Path(args.chunks)
    if not chunk_path.exists():
        logger.error("chunk 库不存在: %s（先运行 scripts/build_corpus.py）", chunk_path)
        return 2

    chunks = load_chunks(chunk_path)
    if not chunks:
        logger.error("chunk 库为空")
        return 1
    logger.info("加载 %d 个 chunk", len(chunks))

    config = RetrievalConfig(
        fusion=args.fusion,
        use_rerank=not args.no_rerank,
        time_filter=not args.no_time_filter,
        enable_table_weight=not args.no_table_weight,
    )
    retriever = Retriever.build(chunks, config=config)
    save_index(retriever, Path(args.index), chunk_path=chunk_path)
    logger.info("索引已保存 → %s", args.index)

    # 自检一条
    hits = retriever.retrieve("2023年营业收入是多少")
    logger.info("自检检索：'2023年营业收入是多少' → %d 条", len(hits))
    for h in hits[:3]:
        logger.info("  [%.3f] %s | %s", h["score"], h["chunk"].source, h["text"][:40].replace("\n", " "))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
