"""W5 评估 —— golden set + 检索指标 + 生成指标 + A/B 对比报告

用法:
    python scripts/run_eval.py                                  # 用 data/index + golden_set.csv
    python scripts/run_eval.py --golden golden_set/demo_golden_set.csv
    python scripts/run_eval.py --index data/index_demo --chunks data/corpus_demo/chunks.json
    python scripts/run_eval.py --gen                            # 生成评估（含数字校验）
    python scripts/run_eval.py --no-compare                     # 不跑 A/B 对比
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("run_eval")

from config.settings import CORPUS_DIR, EVAL_REPORT_DIR, GOLDEN_SET_PATH, INDEX_DIR  # noqa: E402
from src.chunking.chunker import load_chunks  # noqa: E402
from src.eval.golden_set import load_golden_set, type_distribution  # noqa: E402
from src.eval.report import write_generation_report, write_retrieval_report  # noqa: E402
from src.eval.runner import EvalRunner  # noqa: E402
from src.generation.generator import RAGGenerator  # noqa: E402
from src.retrieval.retriever import RetrievalConfig, Retriever, load_index  # noqa: E402


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="RAG 评估（检索 + 生成 + A/B）")
    p.add_argument("--index", default=str(INDEX_DIR), help="索引目录")
    p.add_argument("--chunks", default=str(CORPUS_DIR / "chunks.json"), help="chunk 库")
    p.add_argument("--golden", default=str(GOLDEN_SET_PATH), help="golden set CSV")
    p.add_argument("--outdir", default=str(EVAL_REPORT_DIR), help="报告输出目录")
    p.add_argument("--gen", action="store_true", help="运行生成评估")
    p.add_argument("--ragas", action="store_true", help="生成评估时运行 RAGAS（需安装 ragas）")
    p.add_argument("--no-compare", action="store_true", help="不跑 dense-only 对照实验")
    p.add_argument("--tag", default="", help="实验标签（写入报告）")
    return p.parse_args()


def run_retrieval_on(retriever: Retriever, golden_items, tag: str):
    runner = EvalRunner(retriever, golden_items)
    metrics, per_query = runner.run_retrieval()
    return metrics, per_query


def main() -> int:
    args = parse_args()
    index_dir = Path(args.index)
    chunk_path = Path(args.chunks)
    if not index_dir.exists() or not chunk_path.exists():
        logger.error("索引或 chunk 库不存在（先跑 index_corpus.py）: %s / %s", index_dir, chunk_path)
        return 2

    golden_items = load_golden_set(args.golden)
    if not golden_items:
        logger.error("golden set 为空: %s（先用 build_golden_set.py 生成）", args.golden)
        return 2
    logger.info("golden set: %d 条，类型分布 %s", len(golden_items), type_distribution(golden_items))

    retriever = load_index(index_dir, chunk_path)
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    tag = args.tag or datetime.now().strftime("%Y%m%d_%H%M%S")

    # ---- 当前配置检索评估 ----
    metrics, per_query = run_retrieval_on(retriever, golden_items, tag)
    report = write_retrieval_report(
        outdir / f"retrieval_report_{tag}.md", f"当前配置（{tag}）", metrics, per_query,
        extra={"fusion": retriever.config.fusion, "use_rerank": retriever.config.use_rerank,
               "w_dense": retriever.config.w_dense, "w_sparse": retriever.config.w_sparse,
               "table_weight": retriever.config.table_weight,
               "time_filter": retriever.config.time_filter,
               "report_type_filter": retriever.config.report_type_filter},
    )
    logger.info("检索评估: %s", {k: round(v, 4) if isinstance(v, float) else v for k, v in metrics.items() if k != "n"})
    logger.info("报告 → %s", report)

    # ---- A/B 对照：dense-only（无重排、无表格加权、纯稠密） ----
    if not args.no_compare:
        base_cfg = RetrievalConfig(
            fusion="weighted", w_dense=1.0, w_sparse=0.0,
            use_rerank=False, time_filter=False, enable_table_weight=False,
        )
        base = Retriever(retriever.chunks, dense=retriever.dense, bm25=retriever.bm25, config=base_cfg)
        base_metrics, _ = run_retrieval_on(base, golden_items, tag)
        cmp = _write_comparison(outdir / f"ab_compare_{tag}.md", base_metrics, metrics)
        logger.info("A/B 对比 → %s", cmp)

    # ---- 生成评估 ----
    if args.gen:
        from src.agent.financial_agent import FinancialAgent

        generator = RAGGenerator(retriever)
        agent = FinancialAgent(generator)
        runner = EvalRunner(retriever, golden_items)
        stats, per_query = runner.run_generation(generator, use_ragas=args.ragas, agent=agent)
        greport = write_generation_report(outdir / f"generation_report_{tag}.md", stats, per_query)
        logger.info("生成评估: %s", {k: v for k, v in stats.items() if k != "ragas"})
        logger.info("报告 → %s", greport)

    return 0


def _write_comparison(path: Path, base: dict, cur: dict) -> Path:
    lines = [
        "# A/B 实验对比",
        "",
        "对照组：dense-only（无重排、无表格加权） ｜ 实验组：当前配置",
        "",
        "| 指标 | dense-only | 当前配置 | Δ |",
        "|---|---|---|---|",
    ]
    for k in base:
        if k == "n":
            continue
        b, c = base[k], cur.get(k, 0.0)
        delta = c - b
        lines.append(f"| {k} | {b:.4f} | {c:.4f} | {delta:+.4f} |")
    lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


if __name__ == "__main__":
    raise SystemExit(main())
