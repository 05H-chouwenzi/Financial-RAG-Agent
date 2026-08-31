"""生成演示数据 —— 3 份"示例科技"年报/半年报/公告 PDF + 配套 golden set

用途：在未下载真实数据前，端到端验证 解析→切块→索引→检索→评估→Agent 全链路。
运行后执行：
    python scripts/parse_documents.py --source demo_data/raw --out data/parsed_demo
    python scripts/build_corpus.py --source data/parsed_demo --out data/corpus_demo/chunks.json
    python scripts/index_corpus.py --chunks data/corpus_demo/chunks.json --index data/index_demo
    python scripts/run_eval.py --golden golden_set/demo_golden_set.csv --index data/index_demo --chunks data/corpus_demo/chunks.json
"""
from __future__ import annotations

import logging
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("make_demo_data")

from config.settings import DEMO_DIR  # noqa: E402
from src.eval.golden_set import GoldenItem, save_golden_set  # noqa: E402

COMPANY = "示例科技股份有限公司"
CODE = "DEMO001"
RAW_DIR = DEMO_DIR / "raw" / CODE


# ============================================================
# 演示文档内容（数字与 golden set 严格一致，保证证据可命中）
# ============================================================

def _doc_2022() -> list[tuple]:
    return [
        ("h1", "示例科技股份有限公司2022年年度报告"),
        ("h2", "第一节 公司简介"),
        ("p", "示例科技股份有限公司（以下简称\"公司\"）是一家专注于智能硬件与软件服务的高新技术企业，报告期内持续加大研发投入，主营业务保持稳定增长。"),
        ("h2", "第二节 主要会计数据和财务指标"),
        ("table", [
            ["项目", "2022年", "2021年"],
            ["营业收入(万元)", "52,000", "43,000"],
            ["营业成本(万元)", "33,000", "28,000"],
            ["净利润(万元)", "8,000", "6,500"],
            ["资产总计(万元)", "120,000", "100,000"],
            ["负债合计(万元)", "50,000", "45,000"],
        ]),
        ("h2", "第三节 主营业务分产品情况"),
        ("table", [
            ["产品", "收入(万元)", "占比"],
            ["智能硬件", "30,000", "57.7%"],
            ["软件服务", "15,000", "28.8%"],
            ["其他", "7,000", "13.5%"],
        ]),
        ("h2", "第四节 前十大股东持股情况"),
        ("table", [
            ["股东名称", "持股比例"],
            ["示例控股集团", "35%"],
            ["李四", "12%"],
            ["王五", "8%"],
            ["赵六", "5%"],
        ]),
        ("h2", "第五节 经营情况讨论与分析"),
        ("p", "报告期内，公司实现营业收入52,000万元，同比增长20%；实现净利润8,000万元，同比增长23%。"),
        ("p", "公司毛利率为36.5%，较上年同期略有提升，主要得益于智能硬件产品规模效应显现。"),
    ]


def _doc_2023() -> list[tuple]:
    return [
        ("h1", "示例科技股份有限公司2023年年度报告"),
        ("h2", "第一节 公司简介"),
        ("p", "示例科技股份有限公司（以下简称\"公司\"）是一家专注于智能硬件与软件服务的高新技术企业，2023年继续推进产品升级与市场拓展。"),
        ("h2", "第二节 主要会计数据和财务指标"),
        ("table", [
            ["项目", "2023年", "2022年"],
            ["营业收入(万元)", "68,000", "52,000"],
            ["营业成本(万元)", "41,000", "33,000"],
            ["净利润(万元)", "10,500", "8,000"],
            ["资产总计(万元)", "150,000", "120,000"],
            ["负债合计(万元)", "65,000", "50,000"],
        ]),
        ("h2", "第三节 主营业务分产品情况"),
        ("table", [
            ["产品", "收入(万元)", "占比"],
            ["智能硬件", "40,000", "58.8%"],
            ["软件服务", "20,000", "29.4%"],
            ["其他", "8,000", "11.8%"],
        ]),
        ("h2", "第四节 前十大股东持股情况"),
        ("table", [
            ["股东名称", "持股比例"],
            ["示例控股集团", "35%"],
            ["李四", "12%"],
            ["王五", "8%"],
            ["赵六", "5%"],
        ]),
        ("h2", "第五节 经营情况讨论与分析"),
        ("p", "报告期内，公司实现营业收入68,000万元，同比增长30.77%；实现净利润10,500万元，同比增长31.25%。"),
        ("p", "公司毛利率为39.7%，较上年同期提升3.2个百分点，主要得益于软件服务收入占比提升。"),
    ]


def _doc_h1_2023() -> list[tuple]:
    return [
        ("h1", "示例科技股份有限公司2023年半年度报告"),
        ("h2", "第一节 主要会计数据"),
        ("p", "报告期内，公司实现营业收入31,000万元，实现净利润4,200万元。"),
        ("h2", "第二节 经营情况"),
        ("p", "上半年公司智能硬件出货量稳步增长，软件服务业务收入占比进一步提升。"),
    ]


def _doc_dividend() -> list[tuple]:
    return [
        ("h1", "示例科技股份有限公司2023年度利润分配方案公告"),
        ("p", "公司拟以2023年末总股本为基数，向全体股东每10股派发现金红利3.00元（含税）。"),
        ("p", "本次利润分配方案尚需提交公司股东大会审议通过后方可实施。"),
    ]


# ============================================================
# PDF 生成（reportlab + 中文 CID 字体）
# ============================================================

def _make_pdf(path: Path, title: str, sections: list[tuple]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.units import cm
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.cidfonts import UnicodeCIDFont
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

    pdfmetrics.registerFont(UnicodeCIDFont("STSong-Light"))
    style_h = ParagraphStyle("h", fontName="STSong-Light", fontSize=14, leading=20, spaceAfter=8)
    style_h2 = ParagraphStyle("h2", fontName="STSong-Light", fontSize=12, leading=18, spaceBefore=8, spaceAfter=6)
    style_p = ParagraphStyle("p", fontName="STSong-Light", fontSize=10.5, leading=16, spaceAfter=6)

    doc = SimpleDocTemplate(str(path), pagesize=A4)
    story = []
    story.append(Paragraph(title, style_h))
    story.append(Spacer(1, 6))
    for kind, content in sections:
        if kind == "h1":
            story.append(Paragraph(content, style_h))
        elif kind == "h2":
            story.append(Paragraph(content, style_h2))
        elif kind == "p":
            story.append(Paragraph(content, style_p))
        elif kind == "table":
            data = [[Paragraph(str(c), style_p) for c in row] for row in content]
            t = Table(data, hAlign="LEFT", colWidths=[4 * cm, 3.2 * cm, 3.2 * cm])
            t.setStyle(TableStyle([
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ]))
            story.append(t)
            story.append(Spacer(1, 8))
    doc.build(story)
    logger.info("生成 %s", path)


def make_demo_docs() -> None:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    _make_pdf(RAW_DIR / "ndbg" / "示例科技2022年年度报告.pdf", "示例科技股份有限公司2022年年度报告", _doc_2022())
    _make_pdf(RAW_DIR / "ndbg" / "示例科技2023年年度报告.pdf", "示例科技股份有限公司2023年年度报告", _doc_2023())
    _make_pdf(RAW_DIR / "bndbg" / "示例科技2023年半年度报告.pdf", "示例科技股份有限公司2023年半年度报告", _doc_h1_2023())
    _make_pdf(RAW_DIR / "公告" / "示例科技2023年度利润分配方案公告.pdf", "示例科技股份有限公司2023年度利润分配方案公告", _doc_dividend())


# ============================================================
# 配套 golden set（与上面文档内容严格一致）
# ============================================================

def make_demo_golden_set(out_path: Path) -> None:
    ND = "DEMO001/ndbg"
    BD = "DEMO001/bndbg"
    items = [
        GoldenItem(id="D001", type="fact", question="示例科技2023年的营业收入是多少万元？",
                   answer="68,000万元", doc_ids=f"{ND}/示例科技2023年年度报告",
                   evidence="实现营业收入68,000万元"),
        GoldenItem(id="D002", type="fact", question="示例科技2022年的净利润是多少万元？",
                   answer="8,000万元", doc_ids=f"{ND}/示例科技2022年年度报告",
                   evidence="实现净利润8,000万元"),
        GoldenItem(id="D003", type="calc", question="示例科技2023年的毛利率是多少？",
                   answer="约39.7%", doc_ids=f"{ND}/示例科技2023年年度报告",
                   evidence="营业成本(万元) 41,000"),
        GoldenItem(id="D004", type="compare", question="示例科技2023年净利润相比2022年增长了多少？",
                   answer="同比增长31.25%", doc_ids=f"{ND}/示例科技2023年年度报告",
                   evidence="净利润10,500万元，同比增长31.25%"),
        GoldenItem(id="D005", type="table", question="示例科技2023年前十大股东中持股比例最高的是谁？",
                   answer="示例控股集团（35%）", doc_ids=f"{ND}/示例科技2023年年度报告",
                   evidence="示例控股集团 35%"),
        GoldenItem(id="D006", type="fact", question="示例科技2023年半年报的营业收入是多少万元？",
                   answer="31,000万元", doc_ids=f"{BD}/示例科技2023年半年度报告",
                   evidence="实现营业收入31,000万元"),
        GoldenItem(id="D007", type="multi_doc", question="对比示例科技2022年和2023年的营业收入",
                   answer="2022年52,000万元，2023年68,000万元",
                   doc_ids=f"{ND}/示例科技2022年年度报告;{ND}/示例科技2023年年度报告",
                   evidence="营业收入(万元) 68,000"),
        GoldenItem(id="D008", type="reject", question="示例科技2026年的股价会涨到多少？",
                   answer="应拒答", doc_ids="", evidence=""),
    ]
    save_golden_set(items, out_path)
    logger.info("生成 golden set（%d 条）→ %s", len(items), out_path)


def main() -> int:
    make_demo_docs()
    make_demo_golden_set(DEMO_DIR.parent / "golden_set" / "demo_golden_set.csv")
    print("\n下一步（复制执行）：")
    print("  python scripts/parse_documents.py --source demo_data/raw --out data/parsed_demo")
    print("  python scripts/build_corpus.py --source data/parsed_demo --out data/corpus_demo/chunks.json")
    print("  python scripts/index_corpus.py --chunks data/corpus_demo/chunks.json --index data/index_demo")
    print("  python scripts/run_eval.py --golden golden_set/demo_golden_set.csv --index data/index_demo --chunks data/corpus_demo/chunks.json --gen")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
