# Financial-RAG-Agent

面向 A 股上市公司**年报 / 半年报 / 公告**的垂直金融 RAG 系统。

从 0 到 1 搭建：复杂 PDF 解析（表格 / 多栏 / 扫描件 OCR）→ 结构感知切块 →
BM25 + 稠密混合检索 + 重排 → 生成（引用溯源 / 数字校验 / 拒答），
并用 150 条 golden set + 量化指标（Hit@k / MRR / RAGAS）证明每一层优化的价值。

> 完整规划见 [docs/PROJECT_PLAN.md](docs/PROJECT_PLAN.md)

## 项目结构

```
├── data/          # 原始 PDF / 解析结果 / chunk 库（gitignore）
├── golden_set/    # 评估标注数据与规范
├── experiments/   # 实验记录与对比
├── scripts/       # 一键脚本（下载/解析/检索/评估）
├── src/
│   ├── ingestion/ # 数据获取 + 文档解析
│   ├── chunking/  # 切块策略
│   ├── retrieval/ # 稠密/稀疏/混合/重排
│   ├── generation/# 回答 + 引用 + 数字校验 + 拒答
│   ├── agent/     # 轻量 Agent
│   └── eval/      # 评估框架
├── config/        # 全局配置
├── api/           # 轻量 API demo
└── docs/          # 规划与文档
```

## 快速开始（W1：数据准备）

```bash
pip install -r requirements.txt
cp .env.example .env

# 下载 5 家公司近 3 年年报 + 半年报（示例）
python scripts/download_reports.py --stock-file stocks.example.txt --categories ndbg,bndbg

# 只看查询结果不下载
python scripts/download_reports.py --stocks 600519 --categories ndbg --dry-run
```

## 当前进度

- [x] 项目规划与骨架
- [x] W1 数据下载脚本（巨潮资讯网）
- [ ] W2 文档解析（版面/表格/OCR）
- [ ] W3 切块策略
- [ ] W4 混合检索 + 重排
- [ ] W5 评估体系（golden set + RAGAS）
- [ ] W6 Agent 集成与交付

## 技术栈

Python 3.11 · FastAPI · pdfplumber/PyMuPDF/MinerU · FAISS · bm25s · bge-reranker · RAGAS
