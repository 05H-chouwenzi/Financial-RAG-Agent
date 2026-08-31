"""下载巨潮资讯网定期报告/公告 PDF —— W1 数据准备

用法示例:
    python scripts/download_reports.py --stocks 000001,600519 --categories ndbg,bndbg ^
        --start 2022-01-01 --end 2024-12-31
    python scripts/download_reports.py --stock-file stocks.example.txt --all-categories --dry-run
    python scripts/download_reports.py --stocks 300750 --categories ndbg --limit 3
"""
from __future__ import annotations

import argparse
import logging
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("download_reports")

CATEGORY_HELP = (
    "报告类别，逗号分隔。可选: ndbg(年报) bndbg(半年报) yjdbg(一季报) sjdbg(三季报) "
    "yxjygj(业绩预告) zhgpsqqr(招股说明书)；或 --all-categories"
)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="下载巨潮资讯网定期报告/公告 PDF")
    src = p.add_mutually_exclusive_group(required=True)
    src.add_argument("--stocks", help="逗号分隔的股票代码，如 000001,600519")
    src.add_argument("--stock-file", help="股票清单文件，每行一个代码（可写 代码,备注）")

    p.add_argument("--categories", default="ndbg,bndbg", help=CATEGORY_HELP)
    p.add_argument("--all-categories", action="store_true", help="下载全部支持类别")
    p.add_argument("--start", default="", help="开始日期 YYYY-MM-DD，默认三年前")
    p.add_argument("--end", default="", help="结束日期 YYYY-MM-DD，默认今天")
    p.add_argument("--outdir", default="", help="输出目录，默认 data/raw")
    p.add_argument("--column", default="", help="强制板块列: szse/sse/cyb/kcb/bj（默认按代码推断）")
    p.add_argument("--title-keyword", default="", help="标题必须包含的关键词（默认不限）")
    p.add_argument(
        "--exclude-keyword", default="摘要",
        help="标题排除关键词（默认排除'摘要'；传空字符串 '' 关闭）",
    )
    p.add_argument("--limit", type=int, default=0, help="每股每类最多处理条数（测试用）")
    p.add_argument("--dry-run", action="store_true", help="只查询并打印清单，不下载")
    p.add_argument("--force", action="store_true", help="强制重新下载（覆盖已有文件）")
    return p.parse_args()


def load_stocks(args: argparse.Namespace) -> list[tuple[str, str]]:
    """返回 [(code, name_hint), ...]"""
    if args.stocks:
        out = []
        for item in args.stocks.split(","):
            item = item.strip()
            if item:
                out.append((item, ""))
        return out
    path = Path(args.stock_file)
    if not path.exists():
        raise SystemExit(f"股票清单文件不存在: {path}")
    out = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = [x.strip() for x in line.split(",")]
        code = parts[0]
        name = parts[1] if len(parts) > 1 else ""
        if code:
            out.append((code, name))
    return out


def process_stock(
    client,
    manifest,
    code: str,
    name_hint: str,
    org_id: str,
    categories: list[str],
    start: str,
    end: str,
    outdir: Path,
    args: argparse.Namespace,
) -> int:
    """处理一只股票的指定类别，返回实际新增下载数"""
    from config.settings import CATEGORY_MAP
    from src.ingestion.cninfo import infer_column, safe_filename
    from src.ingestion.manifest import DocRecord

    new_count = 0
    for cat in categories:
        category_code = CATEGORY_MAP[cat]
        columns = [args.column] if args.column else infer_column(code)

        anns: list[dict] = []
        for col in columns:
            anns = client.query_announcements(code, org_id, col, category_code, start, end)
            if anns:
                logger.info("[%s/%s] %s 找到 %d 条公告", code, cat, col, len(anns))
                break
        if not anns:
            logger.info("[%s/%s] 无公告（区间 %s ~ %s）", code, cat, start, end)
            continue

        target = Path(outdir) / code / cat
        seen = 0
        for item in anns:
            title = (item.get("announcementTitle") or "").strip()
            if args.title_keyword and args.title_keyword not in title:
                continue
            if args.exclude_keyword and args.exclude_keyword in title:
                continue
            if args.limit and seen >= args.limit:
                break
            seen += 1

            ts = item.get("announcementTime")
            ann_date = datetime.fromtimestamp(ts / 1000).strftime("%Y-%m-%d") if ts else ""
            url = client.parse_adjunct_url(item)
            fname = f"{code}_{ann_date}_{safe_filename(title)}.pdf"
            fpath = target / fname

            rec = DocRecord(
                code=code, name=name_hint, org_id=org_id, report_type=cat,
                title=title, announce_date=ann_date, url=url,
                file_path=str(fpath),
            )

            if args.dry_run:
                logger.info("  [dry-run] %s", fname)
                continue

            existing = manifest.get(rec)
            if existing and existing.status == "ok" and fpath.exists() and not args.force:
                logger.info("  [skip] %s", fname)
                continue

            try:
                downloaded = client.download(url, fpath, force=args.force)
                manifest.add(rec, overwrite=args.force)
                manifest.mark(rec, "ok")
                if downloaded:
                    logger.info("  [ok] %s", fname)
                    new_count += 1
                else:
                    logger.info("  [exists] %s", fname)
            except Exception as e:  # noqa: BLE001
                manifest.add(rec, overwrite=True)
                manifest.mark(rec, "failed", str(e))
                logger.error("  [failed] %s: %s", fname, e)

    return new_count


def main() -> int:
    args = parse_args()

    from config.settings import (
        CATEGORY_MAP, MANIFEST_PATH, RAW_DIR, REQUEST_DELAY, ensure_dirs,
    )
    from src.ingestion.cninfo import CninfoClient
    from src.ingestion.manifest import Manifest

    ensure_dirs()
    outdir = Path(args.outdir) if args.outdir else RAW_DIR
    outdir.mkdir(parents=True, exist_ok=True)

    categories = list(CATEGORY_MAP) if args.all_categories else [
        c.strip() for c in args.categories.split(",") if c.strip()
    ]
    unknown = [c for c in categories if c not in CATEGORY_MAP]
    if unknown:
        logger.error("未知类别: %s（可选: %s）", ",".join(unknown), ",".join(CATEGORY_MAP))
        return 2

    end = args.end or date.today().isoformat()
    start = args.start or (date.today() - timedelta(days=365 * 3)).isoformat()
    if start > end:
        logger.error("开始日期 %s 晚于结束日期 %s", start, end)
        return 2

    stocks = load_stocks(args)
    if not stocks:
        logger.error("没有可用的股票代码")
        return 2
    logger.info(
        "股票: %s | 类别: %s | 区间: %s ~ %s | 输出: %s",
        ", ".join(s[0] for s in stocks), ",".join(categories), start, end, outdir,
    )

    manifest = Manifest(MANIFEST_PATH)
    client = CninfoClient(delay=REQUEST_DELAY)

    new_total, fail_total = 0, 0
    for code, name_hint in stocks:
        try:
            org_id = client.get_org_id(code)
        except Exception as e:  # noqa: BLE001
            logger.error("[%s] 获取 orgId 失败: %s", code, e)
            fail_total += 1
            continue
        try:
            new_total += process_stock(
                client, manifest, code, name_hint, org_id,
                categories, start, end, outdir, args,
            )
            manifest.save()
        except Exception as e:  # noqa: BLE001
            logger.error("[%s] 处理失败: %s", code, e)
            fail_total += 1

    summary = manifest.summary()
    logger.info(
        "完成：新增 %d，失败 %d；清单状态 %s → %s",
        new_total, fail_total, summary, MANIFEST_PATH,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
