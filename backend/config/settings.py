"""全局配置 —— 从环境变量读取，默认值见 .env.example"""
from __future__ import annotations

import os
from pathlib import Path

# 项目根目录（config/ 的上一级）
BASE_DIR = Path(__file__).resolve().parent.parent

try:
    from dotenv import load_dotenv

    load_dotenv(BASE_DIR / ".env", override=True)  # .env 优先，避免系统残留环境变量覆盖
except Exception:  # dotenv 未安装时静默跳过
    pass


def _get_bool(key: str, default: bool) -> bool:
    return os.getenv(key, str(default)).strip().lower() in ("1", "true", "yes", "on")


# ===== 数据目录 =====
DATA_DIR = Path(os.getenv("DATA_DIR", str(BASE_DIR / "data")))
RAW_DIR = DATA_DIR / "raw"          # 原始 PDF
PARSED_DIR = DATA_DIR / "parsed"    # 结构化解析结果 (LayoutBlock JSON)
CORPUS_DIR = DATA_DIR / "corpus"    # chunk 库
INDEX_DIR = DATA_DIR / "index"      # 检索索引（向量 + BM25）
MANIFEST_PATH = DATA_DIR / "manifest.csv"

# ===== 巨潮资讯网 =====
CNINFO_BASE = os.getenv("CNINFO_BASE", "http://www.cninfo.com.cn")
CNINFO_QUERY_URL = os.getenv(
    "CNINFO_QUERY_URL", f"{CNINFO_BASE}/new/hisAnnouncement/query"
)
CNINFO_TOPSEARCH_URL = os.getenv(
    "CNINFO_TOPSEARCH_URL", f"{CNINFO_BASE}/new/information/topSearch/query"
)
CNINFO_STATIC_BASE = os.getenv("CNINFO_STATIC_BASE", "http://static.cninfo.com.cn")

DOWNLOAD_TIMEOUT = float(os.getenv("DOWNLOAD_TIMEOUT", "30"))
DOWNLOAD_RETRIES = int(os.getenv("DOWNLOAD_RETRIES", "3"))
REQUEST_DELAY = float(os.getenv("REQUEST_DELAY", "0.8"))  # 秒，礼貌限速

# ===== 报告类别（巨潮 category 参数） =====
CATEGORY_MAP = {
    "ndbg": "category_ndbg_szsh",          # 年报
    "bndbg": "category_bndbg_szsh",        # 半年报
    "yjdbg": "category_yjdbg_szsh",        # 一季报
    "sjdbg": "category_sjdbg_szsh",        # 三季报
    "yxjygj": "category_yxjygj_szsh",      # 业绩预告
    "zhgpsqqr": "category_zhgpsqqr_szsh",  # 招股说明书
}

# ===== Embedding =====
# 可选: dashscope（阿里云API） / bge（本地 sentence-transformers） / hash（占位，仅演示）
EMBEDDING_PROVIDER = os.getenv("EMBEDDING_PROVIDER", "dashscope")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "text-embedding-v3")
EMBEDDING_DIM = int(os.getenv("EMBEDDING_DIM", "1024"))

# ===== 重排 =====
RERANK_MODEL = os.getenv("RERANK_MODEL", "BAAI/bge-reranker-v2-m3")
RERANK_ENABLED = _get_bool("RERANK_ENABLED", True)

# ===== LLM（OpenAI 兼容接口，默认阿里云 Dashscope） =====
DASHSCOPE_API_KEY = os.getenv("DASHSCOPE_API_KEY", "")
DASHSCOPE_BASE_URL = os.getenv(
    "DASHSCOPE_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1"
)
LLM_MODEL = os.getenv("LLM_MODEL", "qwen-plus")
LLM_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", "0.2"))
LLM_MAX_TOKENS = int(os.getenv("LLM_MAX_TOKENS", "1024"))

# ===== 切块默认参数 =====
CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "600"))
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "80"))
MAX_TABLE_ROWS = int(os.getenv("MAX_TABLE_ROWS", "30"))  # 超大表按行组分块上限

# ===== 检索默认参数 =====
RETRIEVAL_TOP_K = int(os.getenv("RETRIEVAL_TOP_K", "30"))    # 融合候选数（调大，避免财务表进不了候选）
RETRIEVAL_FINAL_K = int(os.getenv("RETRIEVAL_FINAL_K", "5"))  # 最终返回数
FUSION_W_DENSE = float(os.getenv("FUSION_W_DENSE", "0.5"))
FUSION_W_SPARSE = float(os.getenv("FUSION_W_SPARSE", "0.5"))
TABLE_WEIGHT = float(os.getenv("TABLE_WEIGHT", "2.0"))
REFUSAL_THRESHOLD = float(os.getenv("REFUSAL_THRESHOLD", "0.10"))
STRICT_NUMBERS = _get_bool("STRICT_NUMBERS", True)

# ===== Golden Set / 评估 =====
GOLDEN_SET_PATH = Path(os.getenv("GOLDEN_SET_PATH", str(BASE_DIR / "golden_set" / "golden_set.csv")))
DEMO_GOLDEN_SET_PATH = Path(os.getenv("DEMO_GOLDEN_SET_PATH", str(BASE_DIR / "golden_set" / "demo_golden_set.csv")))
EVAL_REPORT_DIR = Path(os.getenv("EVAL_REPORT_DIR", str(BASE_DIR / "experiments")))

# ===== 演示数据 =====
DEMO_DIR = Path(os.getenv("DEMO_DIR", str(BASE_DIR / "demo_data")))


def ensure_dirs() -> None:
    """确保数据目录存在"""
    for d in (RAW_DIR, PARSED_DIR, CORPUS_DIR, INDEX_DIR, DEMO_DIR / "raw"):
        d.mkdir(parents=True, exist_ok=True)
