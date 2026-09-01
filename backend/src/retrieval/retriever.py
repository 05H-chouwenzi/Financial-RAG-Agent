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
    FINANCIAL_ANCHOR_BONUS,
    FINANCIAL_BOOST,
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

# 财务指标类查询触发词：命中时启用"财务章节锚定"
_FIN_QUERY_KW = ["营业收入", "净利润", "毛利率", "每股收益", "收益率", "总资产", "负债",
                 "不良贷款率", "拨备覆盖率", "净息差", "成本收入比", "现金流", "同比", "增长", "下降",
                 "净资产", "所有者权益", "每股净资产"]
# 指标表核心指标：这些指标的规范答案就落在"主要会计数据/财务指标"表里，
# 命中时把指标表当作"核心块"强锚定（重排加权重）。毛利率等指标（答案在分行业/分产品表）不放进来，
# 避免指标表挤掉正确的分产品表。
_MAIN_TABLE_KW = [k for k in _FIN_QUERY_KW if k != "毛利率"]
# 财务指标表头锚点：年报/半年报里"主要会计数据"表的表头文字
_FIN_SECTION_KW = ["主要会计数据", "会计数据和财务指标", "主要财务指标", "关键指标"]
# 股东/公司名查询触发词：命中时启用"股东信息锚定"（问"控股股东名称"等）
_PARTY_QUERY_KW = ["控股股东", "股东名称", "大股东", "前十大股东", "前十名股东", "持股"]
# 股东信息定义锚点：释义/定义段常见"控股股东…指 公司全称"模式
_PARTY_SECTION_KW = ["控股股东"]


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
    financial_boost: float = FINANCIAL_BOOST  # 指标表 pre-rerank 加权系数（进入重排候选池用）
    financial_anchor_bonus: float = FINANCIAL_ANCHOR_BONUS  # 指标表核心块在重排阶段的额外加分（0-1 尺度）
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
        self.reranker = Reranker(anchor_bonus=self.config.financial_anchor_bonus) if self.config.use_rerank else None

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

    @staticmethod
    def _is_annual_report(h: dict) -> bool:
        """判断 hit 是否来自年报（注意'半年度报告'包含'年度报告'子串，必须排除半年报）"""
        title = h.get("title", "") or ""
        src = (h.get("source", "") or "").replace("\\", "/")
        if "半年度报告" in title or "/bndbg/" in src:
            return False
        return "年度报告" in title or "/ndbg/" in src

    @staticmethod
    def _is_half_year_report(h: dict) -> bool:
        title = h.get("title", "") or ""
        src = (h.get("source", "") or "").replace("\\", "/")
        return "半年度报告" in title or "/bndbg/" in src

    def _apply_report_type_filter(self, query: str, hits: list[dict]) -> list[dict]:
        """报告类型过滤：查询含'半年报/年报'时，优先保留对应报告类型的 chunk"""
        if not self.config.report_type_filter:
            return hits
        if "半年报" in query and "年报" not in query:
            kept = [h for h in hits if self._is_half_year_report(h)]
            return kept if kept else hits
        if "年报" in query and "半年报" not in query:
            kept = [h for h in hits if self._is_annual_report(h)]
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

    def _apply_financial_section_boost(self, query: str, hits: list[dict]) -> list[dict]:
        """财务章节锚定（指标表核心块）：查询含"指标表核心指标"词时，把指标表 chunk 提到前面。

        pdfplumber 常把年报里的指标表解析成 paragraph（而非 table），
        但表头文字（主要会计数据/会计数据和财务指标）稳定保留在 chunk 开头。
        这里做两件事：
        1. pre-rerank 加权（×financial_boost）：保证指标表能进入重排候选池
           （实测 BM25/稠密下"主要会计数据"表常排 100+ 名，不加权根本进不了 top30）；
        2. 打上 _fin_anchor 标记：词法/交叉编码重排阶段再给一次额外加分，
           否则指标表在"词法重叠率主导"的兜底重排里仍会被审计政策段落/半年报段落挤掉。
        只对命中 _MAIN_TABLE_KW 的查询生效：毛利率类查询的答案在"主营业务分行业/分产品"表，
        不锚定指标表，避免把正确表格挤出 top-k。
        """
        if not any(k in query for k in _FIN_QUERY_KW):
            return hits
        is_main_table = any(k in query for k in _MAIN_TABLE_KW)
        # 查询明确问"上半年/半年报"时，半年报指标表也是规范答案；否则默认整年口径 → 年报指标表优先
        prefer_half = any(k in query for k in ("半年报", "上半年", "半年度"))
        for h in hits:
            text = h.get("text", "") or ""
            section = h.get("section_path", "") or ""
            head = text[:200] + section
            if any(k in head for k in _FIN_SECTION_KW):
                h["score"] *= self.config.financial_boost
                if is_main_table:
                    src = h.get("source", "") or ""
                    title = h.get("title", "") or ""
                    # Windows 路径是反斜杠，统一转正斜杠再判断目录类别
                    src_posix = src.replace("\\", "/")
                    is_half = "半年度报告" in title or "/bndbg/" in src_posix
                    is_annual = (not is_half) and ("年度报告" in title or "/ndbg/" in src_posix)
                    # 只有"年报指标表"（或明确问半年时）才打核心块标记，
                    # 避免"2023年净利润"这类整年问题被 2023 半年报指标表抢走排名。
                    if prefer_half or is_annual:
                        h["_fin_anchor"] = True
        hits.sort(key=lambda h: h["score"], reverse=True)
        return hits

    def _apply_party_anchor(self, query: str, hits: list[dict]) -> list[dict]:
        """股东信息锚定：查询问"控股股东/股东名称/大股东"时，提升含"控股股东…指"定义模式的 chunk。

        这类"名称"问题的规范答案常落在年报"释义/第一节 释义"段（如
        '控股股东、集团公司 指 中国贵州茅台酒厂（集团）有限责任公司'），
        但该段文本短、BM25/稠密排名很低，需要单独锚定才能进重排候选池。
        """
        if not any(k in query for k in _PARTY_QUERY_KW):
            return hits
        for h in hits:
            text = h.get("text", "") or ""
            section = h.get("section_path", "") or ""
            head = text[:200] + section
            if any(k in head for k in _PARTY_SECTION_KW) and "指" in head:
                h["score"] *= self.config.financial_boost
                h["_fin_anchor"] = True
        hits.sort(key=lambda h: h["score"], reverse=True)
        return hits

    # ---------- 主入口 ----------

    def retrieve(self, query: str, top_k: Optional[int] = None, final_k: Optional[int] = None) -> list[dict]:
        """混合检索 → 融合 → 重排 → 返回带 chunk 的命中列表"""
        top_k = top_k or self.config.top_k
        final_k = final_k or self.config.final_k
        q = self._rewrite_query(query)

        # 候选池放大：财务指标表（如"主要会计数据"）在 BM25/稠密里常排到 100+ 名，
        # 只取 top_k*2 会让它们进不了融合候选，后续锚定加权无从生效。
        cand = max(top_k * 10, 100)
        dense_hits = self.dense.search(embed_one(q), top_k=cand) if self.dense else []
        sparse_hits = self.bm25.search(q, top_k=cand) if self.bm25 else []

        if self.config.fusion == "rrf":
            fused = fuse_rrf([dense_hits, sparse_hits], top_k=cand)
        else:
            fused = fuse_weighted(dense_hits, sparse_hits, self.config.w_dense, self.config.w_sparse, top_k=cand)

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
        fused = self._apply_financial_section_boost(query, fused)
        fused = self._apply_party_anchor(query, fused)
        fused = fused[:max(top_k, 30)]  # 锚定加权后再截断，避免把低频表挤掉

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
        texts = [c.search_text() for c in chunks]  # 元数据增强文本，见 Chunk.search_text
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
