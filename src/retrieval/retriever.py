"""检索编排 —— 混合检索 + 重排 + 金融增强

金融增强（规划 M4）：
1. 时间/报告期过滤：问题里出现年份时，优先返回对应报告期的 chunk
2. 表格块加权：表格类问题（股东/占比/指标...）对 table 块加权
3. 层级检索：先章节粗筛再段落精检（可选，默认关闭，见 config）
4. 查询改写：LLM 规范金融术语（可选）
"""
from __future__ import annotations

import json
import logging
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Optional

from config.settings import (
    FUSION_W_DENSE,
    FUSION_W_SPARSE,
    RETRIEVAL_FINAL_K,
    RETRIEVAL_TOP_K,
    TABLE_WEIGHT,
)
from src.chunking.chunker import Chunk, load_chunks
from src.retrieval.dense import DenseIndex
from src.retrieval.embedding import embed_one
from src.retrieval.fusion import fuse_rrf, fuse_weighted
from src.retrieval.rerank import Reranker
from src.retrieval.sparse import BM25Index

logger = logging.getLogger("retriever")

_YEAR_RE = re.compile(r"(20\d{2})")
_TABLE_KW = ["股东", "持股", "十大", "占比", "比例", "指标", "利润表", "资产负债表",
             "现金流量", "表格", "前十", "持有", "构成", "结构"]


@dataclass
class RetrievalConfig:
    top_k: int = RETRIEVAL_TOP_K            # 融合后候选数
    final_k: int = RETRIEVAL_FINAL_K        # 重排后返回数
    w_dense: float = FUSION_W_DENSE
    w_sparse: float = FUSION_W_SPARSE
    use_rerank: bool = True
    time_filter: bool = True
    report_type_filter: bool = True          # 半年报/年报 类型过滤
    table_weight: float = TABLE_WEIGHT
    enable_table_weight: bool = True
    query_rewrite: bool = False             # LLM 查询改写（需配置 LLM）
    fusion: str = "rrf"                     # weighted / rrf（默认 rrf，对分数尺度不敏感）
    llm: Optional[object] = None            # 查询改写用的 LLM

    def to_dict(self) -> dict:
        return {k: v for k, v in asdict(self).items() if k != "llm"}


class Retriever:
    def __init__(
        self,
        chunks: list[Chunk],
        dense: Optional[DenseIndex] = None,
        bm25: Optional[BM25Index] = None,
        config: Optional[RetrievalConfig] = None,
    ):
        self.chunks = chunks
        self.dense = dense or DenseIndex()
        self.bm25 = bm25 or BM25Index()
        self.config = config or RetrievalConfig()
        self.reranker = Reranker() if self.config.use_rerank else None

    # ---------- 查询增强 ----------

    def _rewrite_query(self, query: str) -> str:
        if not self.config.query_rewrite or self.config.llm is None:
            return query
        try:
            resp = self.config.llm.chat([
                {"role": "system", "content": "你是金融检索查询改写助手，把口语问题改写成规范的金融检索词，只输出改写结果。"},
                {"role": "user", "content": query},
            ])
            return (resp or query).strip()
        except Exception as e:  # noqa: BLE001
            logger.debug("查询改写失败: %s", e)
            return query

    # ---------- 金融增强 ----------

    def _apply_time_filter(self, query: str, hits: list[dict]) -> list[dict]:
        if not self.config.time_filter:
            return hits
        years = list(dict.fromkeys(_YEAR_RE.findall(query)))  # 去重保序
        if not years:
            return hits
        if len(years) > 1:
            # 对比/多年度问题（如"2023年 vs 2022年"）不做单年度过滤
            return hits
        year = int(years[0])
        kept = [h for h in hits if h.get("period_year") == year]
        return kept if kept else hits  # 过滤后为空则不过滤，避免全空

    def _apply_report_type_filter(self, query: str, hits: list[dict]) -> list[dict]:
        """报告类型过滤：查询含'半年报/年报'时，优先保留对应报告类型的 chunk"""
        if not self.config.report_type_filter:
            return hits
        if "半年报" in query:
            kept = [h for h in hits if "半年度报告" in h.get("title", "") or "bndbg" in h.get("source", "")]
            return kept if kept else hits
        if "年报" in query:
            kept = [h for h in hits if "年度报告" in h.get("title", "") or "ndbg" in h.get("source", "")]
            return kept if kept else hits
        return hits

    def _apply_table_weight(self, query: str, hits: list[dict]) -> list[dict]:
        if not self.config.enable_table_weight:
            return hits
        if not any(k in query for k in _TABLE_KW):
            return hits
        for h in hits:
            if h.get("block_type") == "table":
                h["score"] *= self.config.table_weight
        hits.sort(key=lambda h: h["score"], reverse=True)
        return hits

    # ---------- 主入口 ----------

    def retrieve(self, query: str, top_k: Optional[int] = None, final_k: Optional[int] = None) -> list[dict]:
        """混合检索 → 融合 → 重排 → 返回带 chunk 的命中列表"""
        top_k = top_k or self.config.top_k
        final_k = final_k or self.config.final_k
        q = self._rewrite_query(query)

        dense_hits = self.dense.search(embed_one(q), top_k=max(top_k * 2, 10)) if self.dense else []
        sparse_hits = self.bm25.search(q, top_k=max(top_k * 2, 10)) if self.bm25 else []

        if self.config.fusion == "rrf":
            fused = fuse_rrf([dense_hits, sparse_hits], top_k=top_k)
        else:
            fused = fuse_weighted(dense_hits, sparse_hits, self.config.w_dense, self.config.w_sparse, top_k=top_k)

        # 富化：挂上 chunk 信息
        for h in fused:
            c = self.chunks[h["index"]]
            h["text"] = c.text
            h["chunk"] = c
            h["title"] = c.title
            h["source"] = c.source
            h["company"] = c.company
            h["block_type"] = c.block_type
            h["period_year"] = c.period_year

        fused = self._apply_time_filter(query, fused)
        fused = self._apply_report_type_filter(query, fused)
        fused = self._apply_table_weight(query, fused)

        if self.reranker is not None and len(fused) > 1:
            fused = self.reranker.rerank(q, fused, top_k=final_k)
        else:
            fused = fused[:final_k]
        return fused

    # ---------- 构建索引 ----------

    @classmethod
    def build(cls, chunks: list[Chunk], config: Optional[RetrievalConfig] = None,
              verbose: bool = True) -> "Retriever":
        """从 chunk 库构建稠密 + 稀疏索引"""
        texts = [c.text for c in chunks]
        metas = [{"doc_id": c.doc_id, "block_type": c.block_type,
                  "period_year": c.period_year, "section_path": c.section_path,
                  "source": c.source, "company": c.company, "title": c.title} for c in chunks]
        if verbose:
            logger.info("构建稠密索引（%d 条）...", len(texts))
        dense = DenseIndex()
        dense.add(texts, metas)
        if verbose:
            logger.info("构建 BM25 索引...")
        bm25 = BM25Index()
        bm25.add_documents(texts)
        return cls(chunks, dense=dense, bm25=bm25, config=config)


# ---------- 持久化 ----------

def save_index(retriever: "Retriever", index_dir: Path, chunk_path: Optional[Path] = None) -> None:
    """保存 retriever 的索引到目录（chunks 单独存或一起存）"""
    index_dir = Path(index_dir)
    index_dir.mkdir(parents=True, exist_ok=True)
    retriever.dense.save(index_dir / "dense")
    retriever.bm25.save(index_dir / "bm25.json")
    (index_dir / "config.json").write_text(
        json.dumps(retriever.config.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8"
    )
    if chunk_path is not None:
        from src.chunking.chunker import save_chunks

        save_chunks(retriever.chunks, chunk_path)


def load_index(index_dir: Path, chunk_path: Path, config: Optional[RetrievalConfig] = None) -> "Retriever":
    """从目录加载索引 + chunk 库"""
    index_dir = Path(index_dir)
    chunks = load_chunks(chunk_path)
    dense = DenseIndex.load(index_dir / "dense")
    bm25 = BM25Index.load(index_dir / "bm25.json")
    if config is None:
        cfg_path = index_dir / "config.json"
        if cfg_path.exists():
            data = json.loads(cfg_path.read_text(encoding="utf-8"))
            cfg = RetrievalConfig(**{k: v for k, v in data.items() if k in RetrievalConfig.__dataclass_fields__})
            config = cfg
        else:
            config = RetrievalConfig()
    return Retriever(chunks, dense=dense, bm25=bm25, config=config)
