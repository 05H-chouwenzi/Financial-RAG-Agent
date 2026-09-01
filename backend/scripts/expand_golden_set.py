# -*- coding: utf-8 -*-
"""golden set 扩容：基于 8 份真实年报/半年报的已验证数据，新增 ~50 条高质量条目。

每条 evidence 都是报告中真实存在的原文片段/关键数字（可溯源）。
运行：python scripts/expand_golden_set.py
"""
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.eval.golden_set import GoldenItem, load_golden_set, save_golden_set

M23 = "600519/ndbg/600519_2024-04-03_贵州茅台2023年年度报告"
M22 = "600519/ndbg/600519_2023-03-31_贵州茅台2022年年度报告"
M23H = "600519/bndbg/600519_2023-08-03_贵州茅台2023年半年度报告"
M24H = "600519/bndbg/600519_2024-08-09_贵州茅台2024年半年度报告"
P23 = "000001/ndbg/000001_2024-03-15_2023年年度报告"
P22 = "000001/ndbg/000001_2023-03-09_2022年年度报告"
P23H = "000001/bndbg/000001_2023-08-24_2023年半年度报告"
P24H = "000001/bndbg/000001_2024-08-16_2024年半年度报告"

NEW = [
    # ============ 茅台 2023 年报 ============
    dict(id="R23", type="fact", question="贵州茅台2023年归属于上市公司股东的扣除非经常性损益的净利润是多少亿元？", answer="747.53亿元", doc_ids=M23, evidence="74,752,564,425.52", note="茅台2023年报 主要会计数据"),
    dict(id="R24", type="fact", question="贵州茅台2023年经营活动产生的现金流量净额是多少亿元？", answer="665.93亿元", doc_ids=M23, evidence="66,593,247,721.09", note="茅台2023年报 主要会计数据"),
    dict(id="R25", type="fact", question="贵州茅台2023年末的总资产是多少亿元？", answer="2727.00亿元", doc_ids=M23, evidence="272,699,660,092.25", note="茅台2023年报 主要会计数据"),
    dict(id="R26", type="fact", question="贵州茅台2023年末归属于上市公司股东的净资产是多少亿元？", answer="2156.69亿元", doc_ids=M23, evidence="215,668,571,607.43", note="茅台2023年报 主要会计数据"),
    dict(id="R27", type="fact", question="贵州茅台2023年的基本每股收益是多少元？", answer="59.51元/股", doc_ids=M23, evidence="59.51", note="茅台2023年报 主要财务指标"),
    dict(id="R28", type="calc", question="贵州茅台2023年营业总收入（含利息收入等）是多少亿元？", answer="1505.60亿元", doc_ids=M23, evidence="150,560,330,316.45", note="茅台2023年报 合并利润表 营业总收入"),
    dict(id="R29", type="table", question="贵州茅台2023年直销模式的毛利率是多少？", answer="95.46%", doc_ids=M23, evidence="95.46", note="茅台2023年报 主营业务分销售模式"),
    dict(id="R30", type="table", question="贵州茅台2023年批发代理模式的毛利率是多少？", answer="89.29%", doc_ids=M23, evidence="89.29", note="茅台2023年报 主营业务分销售模式"),
    dict(id="R31", type="table", question="贵州茅台2023年主营业务分地区中，国内和国外哪个毛利率更高，毛利率是多少？", answer="国外，92.18%", doc_ids=M23, evidence="92.18", note="茅台2023年报 主营业务分地区"),
    dict(id="R32", type="table", question="贵州茅台2023年其他系列酒的毛利率是多少？", answer="79.76%", doc_ids=M23, evidence="79.76", note="茅台2023年报 主营业务分产品"),
    dict(id="R33", type="fact", question="贵州茅台2023年度报告中，前十名股东中持股比例最高的是谁，持股多少？", answer="中国贵州茅台酒厂（集团）有限责任公司，54.07%", doc_ids=M23, evidence="54.07", note="茅台2023年报 前十名股东"),
    dict(id="R34", type="fact", question="贵州茅台2023年度报告的控股股东名称是什么？", answer="中国贵州茅台酒厂（集团）有限责任公司", doc_ids=M23, evidence="中国贵州茅台酒厂（集团）有限责任公司", note="茅台2023年报 释义/股东"),
    # ============ 茅台 2022 年报 ============
    dict(id="R35", type="fact", question="贵州茅台2022年归属于上市公司股东的净利润是多少亿元？", answer="627.16亿元", doc_ids=M22, evidence="62,716,443,738.27", note="茅台2022年报 主要会计数据"),
    dict(id="R36", type="fact", question="贵州茅台2022年经营活动产生的现金流量净额是多少亿元？", answer="366.99亿元", doc_ids=M22, evidence="36,698,595,830.03", note="茅台2022年报 主要会计数据"),
    dict(id="R37", type="fact", question="贵州茅台2022年末的总资产是多少亿元？", answer="2543.65亿元", doc_ids=M22, evidence="254,364,804,995.25", note="茅台2022年报 主要会计数据"),
    dict(id="R38", type="fact", question="贵州茅台2022年的基本每股收益是多少元？", answer="49.93元/股", doc_ids=M22, evidence="49.93", note="茅台2022年报 主要财务指标"),
    dict(id="R39", type="fact", question="贵州茅台2022年的加权平均净资产收益率是多少？", answer="30.26%", doc_ids=M22, evidence="30.26", note="茅台2022年报 主要财务指标"),
    dict(id="R40", type="compare", question="贵州茅台2022年营业收入比上年同期增长了多少？", answer="增长16.87%", doc_ids=M22, evidence="16.87", note="茅台2022年报 主要会计数据"),
    dict(id="R41", type="compare", question="贵州茅台2022年归属于上市公司股东的净利润比上年同期增长了多少？", answer="增长19.55%", doc_ids=M22, evidence="19.55", note="茅台2022年报 主要会计数据"),
    # ============ 平安 2023 年报 ============
    dict(id="R42", type="fact", question="平安银行2023年末的拨备覆盖率是多少？", answer="277.63%", doc_ids=P23, evidence="277.63%", note="平安2023年报 主要会计数据"),
    dict(id="R43", type="fact", question="平安银行2023年的净息差是多少？", answer="2.38%", doc_ids=P23, evidence="2.38%", note="平安2023年报 主要会计数据"),
    dict(id="R44", type="fact", question="平安银行2023年的成本收入比是多少？", answer="27.90%", doc_ids=P23, evidence="27.90%", note="平安2023年报 主要会计数据"),
    dict(id="R45", type="fact", question="平安银行2023年末的资本充足率是多少？", answer="13.43%", doc_ids=P23, evidence="13.43%", note="平安2023年报 主要会计数据"),
    dict(id="R46", type="fact", question="平安银行2023年末归属于本行普通股股东的每股净资产是多少？", answer="20.74元/股", doc_ids=P23, evidence="20.74", note="平安2023年报 主要会计数据"),
    dict(id="R47", type="fact", question="平安银行2023年的非利息净收入占比是多少？", answer="28.36%", doc_ids=P23, evidence="28.36%", note="平安2023年报 主要会计数据"),
    dict(id="R48", type="fact", question="平安银行2023年扣除非经常性损益后归属于本行股东的净利润是多少亿元？", answer="464.31亿元", doc_ids=P23, evidence="46,431", note="平安2023年报 主要会计数据"),
    dict(id="R49", type="compare", question="平安银行2023年归属于本行股东的净利润比上年同期增减了多少？", answer="增长2.1%", doc_ids=P23, evidence="2.1%", note="平安2023年报 主要会计数据"),
    dict(id="R50", type="compare", question="平安银行2023年末的不良贷款率比上年末增减了多少个百分点？", answer="上升0.01个百分点（1.06% vs 1.05%）", doc_ids=P23, evidence="1.06%", note="平安2023年报 主要会计数据"),
    # ============ 平安 2022 年报 ============
    dict(id="R51", type="fact", question="平安银行2022年的营业收入是多少亿元？", answer="1798.95亿元", doc_ids=P22, evidence="179,895", note="平安2022年报 主要会计数据"),
    dict(id="R52", type="fact", question="平安银行2022年归属于本行股东的净利润是多少亿元？", answer="455.16亿元", doc_ids=P22, evidence="45,516", note="平安2022年报 主要会计数据"),
    dict(id="R53", type="fact", question="平安银行2022年末的不良贷款率是多少？", answer="1.05%", doc_ids=P22, evidence="1.05%", note="平安2022年报 主要会计数据"),
    dict(id="R54", type="fact", question="平安银行2022年末的拨备覆盖率是多少？", answer="290.28%", doc_ids=P22, evidence="290.28%", note="平安2022年报 主要会计数据"),
    dict(id="R55", type="fact", question="平安银行2022年的加权平均净资产收益率是多少？", answer="12.36%", doc_ids=P22, evidence="12.36%", note="平安2022年报 主要会计数据"),
    dict(id="R56", type="fact", question="平安银行2022年末的资产总额是多少百万元？", answer="5,321,514百万元", doc_ids=P22, evidence="5,321,514", note="平安2022年报 主要会计数据"),
    dict(id="R57", type="compare", question="平安银行2022年营业收入比上年同期增长了多少？", answer="增长6.2%", doc_ids=P22, evidence="6.2%", note="平安2022年报 主要会计数据"),
    dict(id="R58", type="compare", question="平安银行2022年归属于本行股东的净利润比上年同期增长了多少？", answer="增长25.3%", doc_ids=P22, evidence="25.3%", note="平安2022年报 主要会计数据"),
    # ============ 半年报 ============
    dict(id="R59", type="fact", question="贵州茅台2024年上半年的营业收入是多少亿元？", answer="819.31亿元", doc_ids=M24H, evidence="81,930,977,667.75", note="茅台2024半年报 主要会计数据"),
    dict(id="R60", type="fact", question="贵州茅台2024年上半年归属于上市公司股东的净利润是多少亿元？", answer="416.96亿元", doc_ids=M24H, evidence="41,695,610,983.37", note="茅台2024半年报 主要会计数据"),
    dict(id="R61", type="fact", question="贵州茅台2023年上半年的营业收入是多少亿元？", answer="695.76亿元", doc_ids=M23H, evidence="69,576,019,445.77", note="茅台2023半年报 主要会计数据"),
    dict(id="R62", type="fact", question="贵州茅台2024年上半年营业收入比上年同期增长了多少？", answer="增长17.76%", doc_ids=M24H, evidence="17.76", note="茅台2024半年报 主要会计数据"),
    dict(id="R63", type="fact", question="平安银行2024年上半年的营业收入是多少亿元？", answer="771.32亿元", doc_ids=P24H, evidence="77,132", note="平安2024半年报 主要会计数据"),
    dict(id="R64", type="fact", question="平安银行2024年上半年归属于本行股东的净利润是多少亿元？", answer="258.79亿元", doc_ids=P24H, evidence="25,879", note="平安2024半年报 主要会计数据"),
    dict(id="R65", type="fact", question="平安银行2024年6月末的不良贷款率是多少？", answer="1.07%", doc_ids=P24H, evidence="1.07%", note="平安2024半年报 主要会计数据"),
    dict(id="R66", type="fact", question="平安银行2023年上半年的营业收入是多少亿元？", answer="886.10亿元", doc_ids=P23H, evidence="88,610", note="平安2023半年报 主要会计数据"),
    dict(id="R67", type="fact", question="平安银行2023年上半年归属于本行股东的净利润是多少亿元？", answer="253.87亿元", doc_ids=P23H, evidence="25,387", note="平安2023半年报 主要会计数据"),
    dict(id="R68", type="fact", question="平安银行2023年6月末的拨备覆盖率是多少？", answer="291.51%", doc_ids=P23H, evidence="291.51%", note="平安2023半年报 主要会计数据"),
    # ============ 跨期对比 ============
    dict(id="R69", type="multi_doc", question="对比贵州茅台2022年和2023年经营活动产生的现金流量净额", answer="2022年366.99亿元，2023年665.93亿元", doc_ids=f"{M22};{M23}", evidence="36,698,595,830.03;66,593,247,721.09", note="跨期对比"),
    dict(id="R70", type="multi_doc", question="对比贵州茅台2023年上半年和2024年上半年的营业收入", answer="2023年上半年695.76亿元，2024年上半年819.31亿元", doc_ids=f"{M23H};{M24H}", evidence="69,576,019,445.77;81,930,977,667.75", note="跨期对比"),
    dict(id="R71", type="multi_doc", question="对比平安银行2023年上半年和2024年上半年归属于本行股东的净利润", answer="2023年上半年253.87亿元，2024年上半年258.79亿元", doc_ids=f"{P23H};{P24H}", evidence="25,387;25,879", note="跨期对比"),
    dict(id="R72", type="multi_doc", question="对比平安银行2022年和2023年末的拨备覆盖率", answer="2022年末290.28%，2023年末277.63%", doc_ids=f"{P22};{P23}", evidence="290.28%;277.63%", note="跨期对比"),
    # ============ 拒答 ============
    dict(id="R73", type="reject", question="预测贵州茅台2025年的营业收入会是多少？", answer="应拒答", doc_ids="", evidence="", note="预测类"),
    dict(id="R74", type="reject", question="贵州茅台2023年度的股价最高点是多少？", answer="应拒答", doc_ids="", evidence="", note="股价不在知识库"),
    dict(id="R75", type="reject", question="平安银行2024年的分红派息日是哪一天？", answer="应拒答", doc_ids="", evidence="", note="未披露/不在知识库"),
]


def main() -> int:
    path = PROJECT_ROOT / "golden_set" / "golden_set.csv"
    items = load_golden_set(path)
    existing_ids = {it.id for it in items}
    added = 0
    for d in NEW:
        if d["id"] in existing_ids:
            continue
        items.append(GoldenItem(**d))
        added += 1
    save_golden_set(items, path)
    from src.eval.golden_set import type_distribution
    print(f"added {added} items, total {len(items)}; distribution: {type_distribution(items)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
