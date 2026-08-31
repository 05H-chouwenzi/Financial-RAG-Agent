# 实验记录规范

目标：每次改动**可复现、可对比、可追溯**。

## 每条实验包含

| 字段 | 说明 |
|---|---|
| exp_id | 唯一编号，如 E001 |
| date | 日期 |
| stage | 解析 / 切块 / 检索 / 重排 / 生成 |
| change | 改了什么（代码 / 参数 / 模型） |
| baseline | 对照组 exp_id |
| metrics | 指标对比表 |
| conclusion | 结论 + 是否采纳 |

## 指标口径

- **检索**：Hit Rate@5 / Recall@5 / MRR / NDCG（对同一 golden set）
- **表格还原**：行还原率 / 列还原率 / 单元格 F1
- **生成**：RAGAS（faithfulness / answer_relevancy / context_precision）+ 人工抽样打分

## 规则

1. **每次只改一个变量**，避免混淆因素
2. 同一 golden set 全量回归
3. 记录配置、模型版本、随机种子
4. 结论必须带数字，拒绝"感觉更好"

## 模板（experiments/E000_template.md）

```markdown
# E000 - 实验标题
- date: 2026-08-31
- stage: retrieval
- change: ...
- baseline: -

| metric | baseline | this | Δ |
|---|---|---|---|
| Hit@5 | 0.55 | 0.62 | +7.0pt |

## conclusion
...
```
