"""评估报告 —— Markdown 报告生成"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path


def fmt_pct(x: float) -> str:
    return f"{x:.1%}"


def write_retrieval_report(
    path,
    stage: str,
    metrics: dict,
    per_query: list[dict],
    extra: dict | None = None,
) -> Path:
    """写检索评估报告

    metrics: summarize_retrieval 输出
    per_query: [{question, type, hit5, mrr, ...}]
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        f"# 检索评估报告（{stage}）",
        "",
        f"- 生成时间: {datetime.now():%Y-%m-%d %H:%M}",
        f"- 样本数: {metrics.get('n', len(per_query))}",
        "",
        "## 汇总指标",
        "",
        "| 指标 | 值 |",
        "|---|---|",
    ]
    for k, v in metrics.items():
        if k == "n":
            continue
        lines.append(f"| {k} | {v if isinstance(v, str) else fmt_pct(v)} |")

    if extra:
        lines += ["", "## 实验说明", ""]
        for k, v in extra.items():
            lines.append(f"- **{k}**: {v}")

    lines += ["", "## 逐条结果", "", "| # | 类型 | 问题 | Hit@5 | MRR |", "|---|---|---|---|---|"]
    for i, q in enumerate(per_query, 1):
        lines.append(f"| {i} | {q.get('type','')} | {q.get('question','')[:50]} | "
                     f"{fmt_pct(q.get('hit5', 0))} | {q.get('mrr', 0):.3f} |")
    lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def write_generation_report(path, stats: dict, per_query: list[dict]) -> Path:
    """写生成评估报告

    stats: {n, refused, refused_correct, num_check_pass_rate, ragas: {...}}
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        f"# 生成评估报告",
        "",
        f"- 生成时间: {datetime.now():%Y-%m-%d %H:%M}",
        f"- 样本数: {stats.get('n', len(per_query))}",
        "",
        "## 汇总",
        "",
        "| 指标 | 值 |",
        "|---|---|",
    ]
    for k, v in stats.items():
        if k == "n" or k == "ragas":
            continue
        if isinstance(v, float) and v <= 1.0:
            lines.append(f"| {k} | {fmt_pct(v)} |")
        else:
            lines.append(f"| {k} | {v} |")
    if stats.get("ragas"):
        lines += ["", "## RAGAS", "", "| 指标 | 值 |", "|---|---|"]
        for k, v in stats["ragas"].items():
            lines.append(f"| {k} | {v} |")
    lines += ["", "## 逐条结果", "", "| # | 类型 | 问题 | 拒答 | 数字校验 | 回答摘要 |", "|---|---|---|---|---|---|"]
    for i, q in enumerate(per_query, 1):
        lines.append(f"| {i} | {q.get('type','')} | {q.get('question','')[:40]} | "
                     f"{'是' if q.get('refused') else '否'} | "
                     f"{'通过' if not q.get('num_check') else '⚠' + ','.join(q.get('num_check', [])[:3])} | "
                     f"{q.get('answer','')[:60]} |")
    lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")
    return path
