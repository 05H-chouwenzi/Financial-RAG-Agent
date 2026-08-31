"""Golden Set —— 标注数据加载/保存

字段：id / type / question / answer / doc_ids / page / evidence / note
type: fact | table | compare | calc | multi_doc | reject
"""
from __future__ import annotations

import csv
from dataclasses import asdict, dataclass, fields
from pathlib import Path
from typing import Optional


@dataclass
class GoldenItem:
    id: str = ""
    type: str = "fact"
    question: str = ""
    answer: str = ""
    doc_ids: str = ""       # 答案来源文档（如 600519/ndbg/600519_2024-...json）
    page: str = ""
    evidence: str = ""      # 原文证据片段（检索命中判定用）
    note: str = ""

    @classmethod
    def header(cls) -> list[str]:
        return [f.name for f in fields(cls)]

    def to_dict(self) -> dict:
        return asdict(self)


def load_golden_set(path) -> list[GoldenItem]:
    path = Path(path)
    if not path.exists():
        return []
    items: list[GoldenItem] = []
    with open(path, "r", encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            items.append(GoldenItem(**{k: row.get(k, "") for k in GoldenItem.header()}))
    return items


def save_golden_set(items: list[GoldenItem], path) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=GoldenItem.header())
        writer.writeheader()
        for it in items:
            writer.writerow(it.to_dict())


def type_distribution(items: list[GoldenItem]) -> dict:
    dist: dict[str, int] = {}
    for it in items:
        dist[it.type] = dist.get(it.type, 0) + 1
    return dist
