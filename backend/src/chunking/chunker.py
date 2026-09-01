"""切块 —— 结构感知切块（不切破表格）+ 固定切块（对照组）

对应规划 M3：
- StructuralChunker：按标题层级切块，表格整表一块（超大表按行组切并保留表头），
  段落按 chunk_size/overlap 字符切并优先在句号处断开；每个 chunk 附带
  doc_id/公司/报告期/页码/章节路径/block_type 元数据，供时间过滤与引用溯源。
- FixedChunker：项目一的"固定 500/50 字符硬切"实现，用于 A/B 对照组。
"""
from __future__ import annotations

import re
import uuid
from dataclasses import asdict, dataclass, field
from typing import Any, Optional

from src.ingestion.layout import BlockType, LayoutBlock

# 断句边界：句号/感叹/问号/分号/换行
_SENT_BOUNDARY = re.compile(r"[。！？；\n]")
_NUM_RE = re.compile(r"(20\d{2})")


@dataclass
class Chunk:
    """检索最小单元"""

    chunk_id: str = ""
    doc_id: str = ""
    source: str = ""
    title: str = ""
    company: str = ""
    text: str = ""
    block_type: str = "paragraph"
    page: int = 0
    section_path: str = ""
    period_year: Optional[int] = None   # 报告期年份（时间过滤）
    meta: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return asdict(self)

    def search_text(self) -> str:
        """索引检索用文本：元数据前缀 + 原文。

        财务指标表（如"主要会计数据"）原文信息密度低（只有行名+数字），
        拼接公司/标题/年份/章节后，BM25 与稠密向量才能命中"贵州茅台2023年"等查询词。
        """
        parts = [self.company, self.title]
        if self.period_year:
            parts.append(f"{self.period_year}年")
        if self.section_path:
            parts.append(self.section_path)
        prefix = " ".join(x for x in parts if x)
        return f"{prefix}\n{self.text}"

    @classmethod
    def from_dict(cls, d: dict) -> "Chunk":
        known = set(cls.__dataclass_fields__.keys())
        return cls(**{k: v for k, v in d.items() if k in known})


def _extract_year(text: str) -> Optional[int]:
    """从标题/文件名中提取报告期年份"""
    m = _NUM_RE.search(text or "")
    return int(m.group(1)) if m else None


class StructuralChunker:
    """结构感知切块器"""

    def __init__(
        self,
        chunk_size: int = 600,
        overlap: int = 80,
        max_table_rows: int = 30,
    ):
        self.chunk_size = max(chunk_size, 50)
        self.overlap = min(overlap, self.chunk_size // 2)
        self.max_table_rows = max(max_table_rows, 5)

    # ---------- 主入口 ----------

    def chunk_blocks(self, blocks: list[LayoutBlock], doc_meta: dict | None = None) -> list[Chunk]:
        """把一篇文章的 LayoutBlock 列表切成 Chunk 列表

        doc_meta: {company, title, period_year, source} 等文档级元数据
        """
        meta = doc_meta or {}
        chunks: list[Chunk] = []
        section = ""
        for b in sorted(blocks, key=lambda x: (x.page, x.reading_order)):
            if b.block_type == BlockType.TITLE.value:
                section = b.section_path or b.text
                continue
            if b.block_type == BlockType.TABLE.value:
                chunks.extend(self._chunk_table(b, section, meta))
            else:
                chunks.extend(self._chunk_text(b, section, meta))
        # 统一编号
        for i, c in enumerate(chunks):
            c.chunk_id = f"c{meta.get('doc_id', 'doc')}_{i:05d}"
        return chunks

    # ---------- 表格切块 ----------

    def _chunk_table(self, block: LayoutBlock, section: str, meta: dict) -> list[Chunk]:
        rows = block.table or []
        if not rows:
            if block.text:
                return [self._make(block, section, meta, block.text)]
            return []
        header = rows[0]
        header_md = "| " + " | ".join(str(c) for c in header) + " |"

        # 小表：整表一块
        if len(rows) <= self.max_table_rows:
            return [self._make(block, section, meta, block.text or block.table_to_markdown())]

        # 超大表：按行组分块，每块保留表头
        out: list[Chunk] = []
        group_size = self.max_table_rows - 1
        for start in range(1, len(rows), group_size):
            group = [header] + rows[start : start + group_size]
            md = "| " + " | ".join(str(c) for c in group[0]) + " |\n"
            md += "| " + " | ".join(["---"] * len(group[0])) + " |\n"
            for r in group[1:]:
                md += "| " + " | ".join(str(c) for c in r) + " |\n"
            out.append(self._make(block, section, meta, md, group))
        return out

    # ---------- 文本切块 ----------

    def _chunk_text(self, block: LayoutBlock, section: str, meta: dict) -> list[Chunk]:
        text = block.text or ""
        if not text.strip():
            return []
        if len(text) <= self.chunk_size:
            return [self._make(block, section, meta, text)]

        chunks: list[Chunk] = []
        start = 0
        n = len(text)
        while start < n:
            end = min(start + self.chunk_size, n)
            if end < n:
                # 优先在最后一个断句边界处断开
                window = text[start:end]
                m = list(_SENT_BOUNDARY.finditer(window))
                if m:
                    cut = m[-1].end()
                    if cut >= self.chunk_size * 0.5:  # 至少一半长度
                        end = start + cut
            piece = text[start:end].strip()
            if piece:
                chunks.append(self._make(block, section, meta, piece))
            if end >= n:
                break
            start = max(end - self.overlap, start + 1)
        return chunks

    # ---------- 组装 ----------

    def _make(
        self,
        block: LayoutBlock,
        section: str,
        meta: dict,
        text: str,
        table: Optional[list] = None,
    ) -> Chunk:
        heading = f"{section}\n" if section and section not in text[:50] else ""
        return Chunk(
            doc_id=meta.get("doc_id") or block.doc_id,
            source=meta.get("source") or block.source,
            title=meta.get("title", ""),
            company=meta.get("company", ""),
            text=heading + text,
            block_type=block.block_type,
            page=block.page,
            section_path=section,
            period_year=meta.get("period_year") or _extract_year(
                f"{meta.get('title', '')} {block.section_path} {block.text[:100]}"
            ),
            meta={**meta, "table": table} if table else {**meta},
        )


class FixedChunker:
    """固定字符切块（项目一方案，A/B 对照组）"""

    def __init__(self, chunk_size: int = 500, overlap: int = 50):
        self.chunk_size = chunk_size
        self.overlap = overlap

    def chunk_blocks(self, blocks: list[LayoutBlock], doc_meta: dict | None = None) -> list[Chunk]:
        meta = doc_meta or {}
        chunks: list[Chunk] = []
        for b in sorted(blocks, key=lambda x: (x.page, x.reading_order)):
            text = b.text or (b.table_to_markdown() if b.table else "")
            start = 0
            while start < len(text):
                end = start + self.chunk_size
                piece = text[start:end].strip()
                if piece:
                    chunks.append(self._make(b, meta, piece))
                if end >= len(text):
                    break
                start = end - self.overlap
        for i, c in enumerate(chunks):
            c.chunk_id = f"c{meta.get('doc_id', 'doc')}_{i:05d}"
        return chunks

    def _make(self, block: LayoutBlock, meta: dict, text: str) -> Chunk:
        return Chunk(
            doc_id=meta.get("doc_id") or block.doc_id,
            source=meta.get("source") or block.source,
            title=meta.get("title", ""),
            company=meta.get("company", ""),
            text=text,
            block_type=block.block_type,
            page=block.page,
            section_path=block.section_path,
            period_year=meta.get("period_year") or _extract_year(f"{meta.get('title', '')} {block.text[:100]}"),
            meta=dict(meta),
        )


def build_chunks(
    blocks_by_doc: dict[str, list[LayoutBlock]],
    doc_meta: dict[str, dict],
    chunker: str = "structural",
    chunk_size: int = 600,
    overlap: int = 80,
    max_table_rows: int = 30,
) -> list[Chunk]:
    """批量切块：blocks_by_doc {doc_id: blocks}，doc_meta {doc_id: meta}"""
    cls = StructuralChunker if chunker == "structural" else FixedChunker
    if chunker == "structural":
        engine = cls(chunk_size=chunk_size, overlap=overlap, max_table_rows=max_table_rows)
    else:
        engine = cls(chunk_size=chunk_size, overlap=overlap)
    chunks: list[Chunk] = []
    for doc_id, blocks in blocks_by_doc.items():
        chunks.extend(engine.chunk_blocks(blocks, doc_meta.get(doc_id) or {}))
    return chunks


def save_chunks(chunks: list[Chunk], path: Any) -> None:
    import json
    from pathlib import Path

    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump([c.to_dict() for c in chunks], f, ensure_ascii=False, indent=1)


def load_chunks(path: Any) -> list[Chunk]:
    import json
    from pathlib import Path

    with open(Path(path), "r", encoding="utf-8") as f:
        return [Chunk.from_dict(d) for d in json.load(f)]
