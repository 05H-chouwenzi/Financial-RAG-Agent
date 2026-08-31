"""版面结构 —— LayoutBlock：所有解析器的统一输出结构

设计目的：
- 项目一里 PDF/表格被"平铺成文本"导致结构丢失；这里把文本、表格、标题、
  阅读顺序、章节路径都结构化保留，为后续"结构感知切块"和"表格问答"打地基。
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any, Optional


class BlockType(str, Enum):
    """版面块类型"""
    TITLE = "title"            # 标题（带层级）
    PARAGRAPH = "paragraph"    # 正文段落
    TABLE = "table"            # 表格（保留二维结构）
    LIST = "list"              # 列表
    IMAGE = "image"            # 图片（OCR 文本）
    HEADER = "header"          # 页眉
    FOOTER = "footer"          # 页脚/页码


@dataclass
class LayoutBlock:
    """一个版面块"""

    doc_id: str = ""                            # 文档唯一 ID（源文件相对路径）
    block_type: str = BlockType.PARAGRAPH.value
    text: str = ""                              # 文本内容（表格为渲染后的 Markdown）
    table: Optional[list[list[str]]] = None     # 表格原始二维结构
    page: int = 0                               # 页码（1 起）
    bbox: Optional[list] = None                 # [x0, y0, x1, y1]
    reading_order: int = 0                      # 块在文档中的阅读顺序
    section_path: str = ""                      # 章节路径，如 "第三节 经营情况/收入分析"
    title_level: int = 0                        # 标题层级（0=非标题）
    source: str = ""                            # 源文件路径
    meta: dict = field(default_factory=dict)    # 扩展元数据

    # ---------- 序列化 ----------

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "LayoutBlock":
        known = set(cls.__dataclass_fields__.keys())
        return cls(**{k: v for k, v in d.items() if k in known})

    # ---------- 工具 ----------

    def table_to_markdown(self) -> str:
        """把二维表格渲染成 Markdown 表格（竖线转义，避免破坏结构）"""
        if not self.table:
            return self.text or ""
        rows = [r for r in self.table if any(str(c).strip() for c in r)]
        if not rows:
            return ""
        ncols = max(len(r) for r in rows)
        out: list[str] = []
        header = [str(c).replace("|", "\\|") for c in rows[0]]
        header += [""] * (ncols - len(header))
        out.append("| " + " | ".join(header) + " |")
        out.append("| " + " | ".join(["---"] * ncols) + " |")
        for r in rows[1:]:
            cells = [str(c).replace("|", "\\|") for c in r]
            cells += [""] * (ncols - len(cells))
            out.append("| " + " | ".join(cells) + " |")
        return "\n".join(out)


def save_blocks(blocks: list[LayoutBlock], path: Any) -> None:
    """保存 LayoutBlock 列表到 JSON"""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump([b.to_dict() for b in blocks], f, ensure_ascii=False, indent=1)


def load_blocks(path: Any) -> list[LayoutBlock]:
    """从 JSON 加载 LayoutBlock 列表"""
    with open(path, "r", encoding="utf-8") as f:
        return [LayoutBlock.from_dict(d) for d in json.load(f)]


from pathlib import Path  # noqa: E402  (放在末尾避免循环依赖，保持函数签名可用)
