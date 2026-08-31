"""全局配置 —— 从环境变量读取，默认值见 .env.example"""
from __future__ import annotations

import os
from pathlib import Path

# 项目根目录（config/ 的上一级）
BASE_DIR = Path(__file__).resolve().parent.parent

try:
    from dotenv import load_dotenv

    load_dotenv(BASE_DIR / ".env")
except Exception:  # dotenv 未安装时静默跳过
    pass

# ===== 数据目录 =====
DATA_DIR = Path(os.getenv("DATA_DIR", str(BASE_DIR / "data")))
RAW_DIR = DATA_DIR / "raw"          # 原始 PDF
PARSED_DIR = DATA_DIR / "parsed"    # 结构化解析结果 (LayoutBlock JSON)
CORPUS_DIR = DATA_DIR / "corpus"    # chunk 库
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


def ensure_dirs() -> None:
    """确保数据目录存在"""
    for d in (RAW_DIR, PARSED_DIR, CORPUS_DIR):
        d.mkdir(parents=True, exist_ok=True)
