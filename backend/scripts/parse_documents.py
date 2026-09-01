"""W2 文档解析 —— raw/ 下所有文档 → parsed/ 结构化 LayoutBlock JSON + 解析质量报告

用法:
    python scripts/parse_documents.py                      # 解析 data/raw
    python scripts/parse_documents.py --source demo_data/raw --out data/parsed_demo
    python scripts/parse_documents.py --suffix pdf --use-heavy
    python scripts/parse_documents.py --report data/parsed/parse_report.md
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
from collections import Counter
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("parse_documents")

from config.settings import PARSED_DIR, RAW_DIR, ensure_dirs  # noqa: E402
from src.ingestion.layout import BlockType, save_blocks  # noqa: E402
from src.ingestion.parsers import SUPPORTED_SUFFIXES, parse_document  # noqa: E402


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="解析文档为 LayoutBlock 结构化 JSON")
    p.add_argument("--source", default=str(RAW_DIR), help="原始文档目录（递归扫描）")
    p.add_argument("--out", default=str(PARSED_DIR), help="输出目录")
    p.add_argument("--suffix", default="", help="只解析指定后缀（如 pdf），默认全部支持格式")
    p.add_argument("--use-heavy", action="store_true", help="优先使用重武器解析（MinerU/PaddleOCR）")
    p.add_argument("--report", default="", help="解析质量报告输出路径（默认 <out>/parse_report.md）")
    p.add_argument("--limit", type=int, default=0, help="最多解析文件数（测试用）")
    return p.parse_args()


def collect_files(source: Path, suffix: str) -> list[Path]:
    files = [f for f in source.rglob("*") if f.is_file() and f.suffix.lower() in SUPPORTED_SUFFIXES]
    if suffix:
        files = [f for f in files if f.suffix.lower() == suffix.lower()]
    return sorted(files)


def main() -> int:
    args = parse_args()
    source = Path(args.source)
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    if not source.exists():
        logger.error("源目录不存在: %s", source)
        return 2

    files = collect_files(source, args.suffix)
    if not files:
        logger.warning("没有找到可解析的文档（%s）", source)
        return 0
    if args.limit:
        files = files[: args.limit]
    logger.info("待解析 %d 个文件", len(files))

    stats = {"total": 0, "ok": 0, "failed": 0, "tables": 0, "blocks": 0, "chars": 0}
    failures: list[dict] = []
    per_doc: dict[str, dict] = {}

    for f in files:
        rel = f.relative_to(source)
        doc_id = str(rel).replace("\\", "/")
        out_path = out_dir / rel.with_suffix(".json")
        try:
            blocks = parse_document(f, doc_id=doc_id, use_heavy=args.use_heavy)
            save_blocks(blocks, out_path)
            n_table = sum(1 for b in blocks if b.block_type == BlockType.TABLE.value)
            n_chars = sum(len(b.text or "") for b in blocks)
            stats["ok"] += 1
            stats["tables"] += n_table
            stats["blocks"] += len(blocks)
            stats["chars"] += n_chars
            per_doc[str(rel)] = {"blocks": len(blocks), "tables": n_table, "chars": n_chars}
            logger.info("  [ok] %s (%d 块, %d 表格)", rel, len(blocks), n_table)
        except Exception as e:  # noqa: BLE001
            stats["failed"] += 1
            failures.append({"file": str(rel), "error": str(e)})
            logger.error("  [failed] %s: %s", rel, e)

    # 解析质量报告
    report_path = Path(args.report) if args.report else out_dir / "parse_report.md"
    _write_report(report_path, source, stats, failures, per_doc)
    logger.info(
        "完成: ok=%d failed=%d 表格=%d 块=%d 字符=%d → %s",
        stats["ok"], stats["failed"], stats["tables"], stats["blocks"], stats["chars"], report_path,
    )
    return 0


def _write_report(path: Path, source: Path, stats: dict, failures: list, per_doc: dict) -> None:
    lines = [
        "# 文档解析质量报告",
        "",
        f"- 源目录: `{source}`",
        f"- 生成时间: {__import__('datetime').datetime.now():%Y-%m-%d %H:%M}",
        f"- 解析成功: {stats['ok']} / 失败: {stats['failed']}",
        f"- 总块数: {stats['blocks']}（其中表格块: {stats['tables']}）",
        f"- 总字符数: {stats['chars']}",
        "",
        "## 每文档统计",
        "",
        "| 文档 | 块数 | 表格 | 字符数 |",
        "|---|---|---|---|",
    ]
    for name, d in sorted(per_doc.items()):
        lines.append(f"| {name} | {d['blocks']} | {d['tables']} | {d['chars']} |")
    if failures:
        lines += ["", "## 失败清单", ""]
        for f in failures:
            lines.append(f"- {f['file']}: {f['error']}")
    lines += ["", "## 说明", "", "基线解析使用 pdfplumber（文本+表格）。",
              "扫描件/复杂版面建议启用重武器（MinerU / PaddleOCR PP-Structure）。"]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
