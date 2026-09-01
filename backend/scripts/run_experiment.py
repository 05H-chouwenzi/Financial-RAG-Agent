"""实验 A/B —— 对比两个索引/配置的检索指标

用法:
    python scripts/run_experiment.py --index-a data/index --index-b data/index_rrf \
        --chunks data/corpus/chunks.json --golden golden_set/golden_set.csv
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
logger = logging.getLogger("run_experiment")

from config.settings import CORPUS_DIR, GOLDEN_SET_PATH, INDEX_DIR  # noqa: E402
from src.eval.golden_set import load_golden_set  # noqa: E402
from src.eval.runner import EvalRunner  # noqa: E402
from src.retrieval.retriever import load_index  # noqa: E402


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="A/B 实验：对比两个索引的检索指标")
    p.add_argument("--index-a", default=str(INDEX_DIR))
    p.add_argument("--index-b", required=True)
    p.add_argument("--chunks", default=str(CORPUS_DIR / "chunks.json"))
    p.add_argument("--golden", default=str(GOLDEN_SET_PATH))
    p.add_argument("--label-a", default="A")
    p.add_argument("--label-b", default="B")
    return p.parse_args()


def main() -> int:
    args = parse_args()
    golden = load_golden_set(args.golden)
    if not golden:
        logger.error("golden set 为空: %s", args.golden)
        return 2

    ra = load_index(args.index_a, args.chunks)
    rb = load_index(args.index_b, args.chunks)
    ma, _ = EvalRunner(ra, golden).run_retrieval()
    mb, _ = EvalRunner(rb, golden).run_retrieval()

    print(f"\n=== A/B 实验：{args.label_a} vs {args.label_b} ===")
    print(f"{'指标':<12}{args.label_a:>10}{args.label_b:>10}{'Δ':>10}")
    for k in ma:
        if k == "n":
            continue
        va, vb = ma[k], mb.get(k, 0.0)
        print(f"{k:<12}{va:>10.4f}{vb:>10.4f}{vb - va:>+10.4f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
