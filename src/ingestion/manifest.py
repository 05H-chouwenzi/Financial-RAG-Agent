"""文档清单（manifest）管理 —— 记录已下载文档与状态，支持断点续传"""
from __future__ import annotations

import csv
from dataclasses import asdict, dataclass, fields
from datetime import datetime
from pathlib import Path
from typing import Optional


@dataclass
class DocRecord:
    code: str = ""            # 股票代码
    name: str = ""            # 公司简称
    org_id: str = ""
    report_type: str = ""     # 类别键，如 ndbg
    title: str = ""           # 公告标题
    announce_date: str = ""   # 公告日期 YYYY-MM-DD
    url: str = ""
    file_path: str = ""       # 本地文件路径
    status: str = "pending"   # pending / ok / failed / dry-run
    error: str = ""
    created_at: str = ""

    @classmethod
    def header(cls) -> list[str]:
        return [f.name for f in fields(cls)]

    def to_dict(self) -> dict:
        return asdict(self)


class Manifest:
    """CSV 清单：以 (code, report_type, announce_date, title) 去重"""

    def __init__(self, path: Path):
        self.path = Path(path)
        self.records: list[DocRecord] = []
        self._index: dict[tuple, DocRecord] = {}
        self._load()

    def _load(self) -> None:
        if not self.path.exists():
            return
        with open(self.path, "r", encoding="utf-8-sig", newline="") as f:
            for row in csv.DictReader(f):
                rec = DocRecord(**{k: row.get(k, "") for k in DocRecord.header()})
                self.records.append(rec)
                self._index[self._key(rec)] = rec

    @staticmethod
    def _key(rec: DocRecord) -> tuple:
        return (rec.code, rec.report_type, rec.announce_date, rec.title)

    def has(self, rec: DocRecord) -> bool:
        return self._key(rec) in self._index

    def get(self, rec: DocRecord) -> Optional[DocRecord]:
        return self._index.get(self._key(rec))

    def add(self, rec: DocRecord, overwrite: bool = False) -> bool:
        """新增或更新记录；返回是否新增"""
        key = self._key(rec)
        if key in self._index:
            if not overwrite:
                return False
            old = self._index[key]
            idx = self.records.index(old)
            self.records[idx] = rec
            self._index[key] = rec
            return False
        self.records.append(rec)
        self._index[key] = rec
        return True

    def mark(self, rec: DocRecord, status: str, error: str = "") -> None:
        """更新记录状态"""
        rec.status = status
        rec.error = error
        if not rec.created_at:
            rec.created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.path, "w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=DocRecord.header())
            writer.writeheader()
            for rec in self.records:
                writer.writerow(rec.to_dict())

    def summary(self) -> dict:
        counts: dict[str, int] = {}
        for rec in self.records:
            counts[rec.status] = counts.get(rec.status, 0) + 1
        return counts
