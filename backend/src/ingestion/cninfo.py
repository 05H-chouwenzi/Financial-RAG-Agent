"""巨潮资讯网 (cninfo) 数据下载客户端

公开接口（无需登录）：
- 股票搜索（获取 orgId）:  POST {CNINFO_BASE}/new/information/topSearch/query
- 公告列表:                POST {CNINFO_BASE}/new/hisAnnouncement/query
- PDF 静态资源:            {CNINFO_STATIC_BASE}/finalpage/...

用法参考 scripts/download_reports.py
"""
from __future__ import annotations

import logging
import re
import time
from pathlib import Path
from typing import Optional

import requests

from config.settings import (
    CNINFO_BASE,
    CNINFO_QUERY_URL,
    CNINFO_STATIC_BASE,
    CNINFO_TOPSEARCH_URL,
    DOWNLOAD_RETRIES,
    DOWNLOAD_TIMEOUT,
    REQUEST_DELAY,
)

logger = logging.getLogger("cninfo")

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Referer": CNINFO_BASE + "/",
    "X-Requested-With": "XMLHttpRequest",
    "Accept": "application/json, text/javascript, */*; q=0.01",
}


class CninfoError(RuntimeError):
    """巨潮接口错误"""


def infer_column(code: str) -> list[str]:
    """根据股票代码推断可能的板块列（用于公告查询）"""
    c = code.strip().zfill(6)
    if c.startswith(("688", "689")):
        return ["kcb"]      # 科创板
    if c.startswith(("300", "301", "302")):
        return ["cyb"]      # 创业板
    if c.startswith(("4", "8", "92")):
        return ["bj"]       # 北交所
    if c.startswith("6"):
        return ["sse"]      # 上交所主板
    return ["szse"]         # 深交所主板/中小板


def safe_filename(name: str, max_len: int = 80) -> str:
    """清洗文件名：去除非法字符并截断"""
    cleaned = re.sub(r'[\\/:*?"<>|\r\n\t]', "_", name)
    cleaned = re.sub(r"\s+", " ", cleaned).strip(" .")
    return cleaned[:max_len] or "untitled"


class CninfoClient:
    """巨潮资讯网 HTTP 客户端（带限速与重试）"""

    def __init__(self, session: Optional[requests.Session] = None, delay: float = REQUEST_DELAY):
        self.session = session or requests.Session()
        self.session.headers.update(HEADERS)
        self.delay = delay

    # ---------- 基础请求 ----------

    def _post_json(self, url: str, data: dict):
        last_err: Optional[Exception] = None
        for attempt in range(DOWNLOAD_RETRIES):
            try:
                resp = self.session.post(url, data=data, timeout=DOWNLOAD_TIMEOUT)
                resp.raise_for_status()
                return resp.json()
            except (requests.RequestException, ValueError) as e:
                last_err = e
                time.sleep(self.delay * (attempt + 1))
        raise CninfoError(f"POST {url} 失败: {last_err}")

    # ---------- 股票信息 ----------

    def get_org_id(self, code: str) -> str:
        """获取股票在巨潮的 orgId（查询公告列表必需）"""
        resp = self._post_json(CNINFO_TOPSEARCH_URL, {"keyWord": code, "maxNum": 10})
        if not isinstance(resp, list):
            raise CninfoError(f"topSearch 返回格式异常: {resp!r}")
        for item in resp:
            if str(item.get("code")) == code and item.get("orgId"):
                return str(item["orgId"])
        for item in resp:
            if str(item.get("code", "")).startswith(code) and item.get("orgId"):
                return str(item["orgId"])
        codes = [x.get("code") for x in resp]
        raise CninfoError(f"未找到 {code} 的 orgId，返回: {codes}")

    # ---------- 公告列表 ----------

    def query_announcements(
        self,
        code: str,
        org_id: str,
        column: str,
        category: str,
        start_date: str,
        end_date: str,
        page_size: int = 30,
        max_pages: int = 50,
    ) -> list[dict]:
        """分页查询公告列表（含报告期过滤），返回公告原始字典列表"""
        anns: list[dict] = []
        for page in range(1, max_pages + 1):
            data = {
                "pageNum": str(page),
                "pageSize": str(page_size),
                "column": column,
                "tabName": "fulltext",
                "plate": "",
                "stock": f"{code},{org_id}",
                "searchkey": "",
                "secid": "",
                "category": category,
                "trade": "",
                "seDate": f"{start_date}~{end_date}",
                "sortName": "",
                "sortType": "",
                "isHLtitle": "true",
            }
            payload = self._post_json(CNINFO_QUERY_URL, data)
            items = payload.get("announcements") or []
            anns.extend(items)
            if not payload.get("hasMore") or len(items) < page_size:
                break
            time.sleep(self.delay)
        return anns

    # ---------- 下载 ----------

    def parse_adjunct_url(self, item: dict) -> str:
        """把公告里的 adjunctUrl 拼成完整下载地址"""
        url = item.get("adjunctUrl", "")
        if not url:
            raise CninfoError(
                f"公告缺少 adjunctUrl: {item.get('announcementTitle')}"
            )
        if url.startswith("http"):
            return url
        return f"{CNINFO_STATIC_BASE}/{url.lstrip('/')}"

    def download(self, url: str, dest: Path, force: bool = False) -> bool:
        """下载文件到 dest。已存在且非 force 时跳过。返回是否实际下载。"""
        if dest.exists() and dest.stat().st_size > 0 and not force:
            return False
        dest.parent.mkdir(parents=True, exist_ok=True)
        tmp = dest.with_suffix(dest.suffix + ".part")
        last_err: Optional[Exception] = None
        for attempt in range(DOWNLOAD_RETRIES):
            try:
                with self.session.get(url, stream=True, timeout=DOWNLOAD_TIMEOUT) as resp:
                    resp.raise_for_status()
                    with open(tmp, "wb") as f:
                        for chunk in resp.iter_content(chunk_size=8192):
                            if chunk:
                                f.write(chunk)
                tmp.replace(dest)
                return True
            except (requests.RequestException, OSError) as e:
                last_err = e
                time.sleep(self.delay * (attempt + 1))
        raise CninfoError(f"下载 {url} 失败: {last_err}")
