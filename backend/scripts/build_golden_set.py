"""W5 Golden Set 生成 —— 从 chunk 库自动出题草稿（LLM 辅助），人工校验后入库

流程：
1. 从 corpus 随机/按类型采样 chunk
2. 有 LLM 时让 LLM 根据 chunk 出题（question/answer/type）
3. 无 LLM 时按模板生成占位草稿
4. 输出 golden_set/draft.csv → 人工校验后另存为 golden_set.csv

用法:
    python scripts/build_golden_set.py --chunks data/corpus/chunks.json
    python scripts/build_golden_set.py --n 20 --type fact
    python scripts/build_golden_set.py --out golden_set/draft.csv
"""
from __future__ import annotations

import argparse
import logging
import random
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("build_golden_set")

from config.settings import CORPUS_DIR, DEMO_GOLDEN_SET_PATH  # noqa: E402
from src.chunking.chunker import load_chunks  # noqa: E402
from src.eval.golden_set import GoldenItem, save_golden_set  # noqa: E402
from src.generation.llm import LLMClient  # noqa: E402

_TYPE_POOL = ["fact", "table", "compare", "calc", "multi_doc", "reject"]


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="生成 golden set 草稿")
    p.add_argument("--chunks", default=str(CORPUS_DIR / "chunks.json"), help="chunk 库")
    p.add_argument("--out", default=str(DEMO_GOLDEN_SET_PATH), help="输出草稿 CSV")
    p.add_argument("--n", type=int, default=10, help="生成条数")
    p.add_argument("--type", default="", choices=_TYPE_POOL, help="指定问题类型（默认混合）")
    p.add_argument("--seed", type=int, default=42)
    return p.parse_args()


def main() -> int:
    args = parse_args()
    chunks = load_chunks(args.chunks)
    if not chunks:
        logger.error("chunk 库为空: %s", args.chunks)
        return 2

    random.seed(args.seed)
    sampled = random.sample(chunks, min(args.n, len(chunks)))
    llm = LLMClient()
    items: list[GoldenItem] = []

    for i, c in enumerate(sampled, 1):
        qtype = args.type or random.choice(_TYPE_POOL)
        item = _generate_one(c, qtype, i, llm)
        if item:
            items.append(item)

    save_golden_set(items, args.out)
    logger.info("生成 %d 条草稿 → %s（请人工校验后再作为正式 golden set）", len(items), args.out)
    return 0


def _generate_one(chunk, qtype: str, i: int, llm: LLMClient) -> GoldenItem | None:
    """用 LLM 或模板生成一条 golden item"""
    text = chunk.text[:800]
    doc_id = chunk.doc_id
    prompt = (
        "根据下面这段年报/公告资料，出一道<{qtype}>类型的金融问答题目。\n"
        "严格输出 JSON：{{\"question\": \"...\", \"answer\": \"...\", \"evidence\": \"原文关键句\"}}\n"
        "要求：答案必须能从资料中找到，evidence 必须是原文。\n\n资料：\n{text}"
    ).format(qtype=qtype, text=text)

    if llm.available:
        try:
            import json

            raw = llm.chat([{"role": "user", "content": prompt}])
            data = json.loads(raw[raw.find("{"): raw.rfind("}") + 1])
            return GoldenItem(
                id=f"G{i:04d}", type=qtype,
                question=data.get("question", ""),
                answer=data.get("answer", ""),
                doc_ids=doc_id,
                evidence=data.get("evidence", ""),
                note="LLM草稿，待人工校验",
            )
        except Exception as e:  # noqa: BLE001
            logger.debug("LLM 出题失败（%s），走模板", e)

    # 模板兜底（无 LLM 时）
    head = text[:60].replace("\n", " ")
    return GoldenItem(
        id=f"G{i:04d}", type=qtype,
        question=f"关于{chunk.title or chunk.company}，资料中提到：{head}…",
        answer=text[:120],
        doc_ids=doc_id,
        evidence=text[:60],
        note="模板草稿，请人工改写",
    )


if __name__ == "__main__":
    raise SystemExit(main())
