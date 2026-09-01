# Financial-RAG-Agent

面向 A 股上市公司**年报 / 半年报 / 公告**的垂直金融 RAG 系统。

从 PDF 解析到生成回答的完整链路：复杂文档解析 → 结构感知切块 → 混合检索（BM25 + 稠密向量 + RRF 融合 + 重排）→ LLM 生成（引用溯源 / 数字校验 / 拒答），并用 golden set + 量化指标（Hit@k / MRR / NDCG / RAGAS）证明每一层优化的价值。

## 功能特性

- **数据获取**：巨潮资讯网年报/半年报/公告下载（限速 + 重试 + 断点续传 manifest）
- **文档解析**：pdfplumber 文本层 + 表格层，输出结构化 `LayoutBlock`（页码 / 章节路径 / 阅读顺序）；预留 MinerU / PaddleOCR 集成点
- **结构感知切块**：按章节切块、不切破表格，chunk 带公司 / 报告期 / 章节 / 类型元数据
- **混合检索**：bge 稠密向量 + 自实现 BM25 + RRF 融合 + bge-reranker 重排
- **金融增强**：候选池放大、财务章节锚定（指标表核心块）、元数据增强检索文本、股票代码→公司名映射、年报/半年报口径区分、时间过滤
- **安全生成**：DeepSeek LLM + 引用溯源 + 数字校验（支持万元/亿元/百万元单位换算）+ 拒答
- **评估闭环**：golden set + Hit@k / MRR / NDCG / RAGAS + A/B 对照，每次改动可复现对比
- **前端**：FinFlow 研报检索工作台（Next.js 16 + shadcn/ui），知识库与后端真实语料打通（上传 → 重建索引 → 可被问答检索）

## 系统架构

```text
巨潮 PDF ──▶ 解析(LayoutBlock) ──▶ 结构感知切块 ──▶ 索引(bge向量 + BM25)
                                                          │
用户问题 ──▶ 查询增强 ──▶ 混合检索(RRF) ──▶ 重排(bge-reranker) ──▶ 生成(引用/数字校验/拒答) ──▶ 回答
                                                          │
                        golden set + Hit@k/MRR/NDCG/RAGAS 评估闭环
```

## 评估结果（真实数据）

语料：巨潮下载 8 份真实年报/半年报（贵州茅台 600519、平安银行 000001，2022~2024）。
Golden set：75 条，覆盖 fact / table / calc / compare / multi_doc / reject 六类，证据可溯源。

| 环节 | 指标 | 结果 |
|---|---|---|
| 检索（词法重排，69 条） | HitRate@5 / MRR | **100% / 81.5%** |
| 检索（bge 真实重排，19 条） | HitRate@5 / MRR | **100% / 96.1%** |
| 生成 | 拒答准确率 / 数字校验通过率 | **100% / 100%** |
| RAGAS（19 条子集） | faithfulness / answer_relevancy | 0.59 / 0.96 |
| RAGAS | context_precision / context_recall | 0.78 / 1.00 |

优化演进：hash 占位向量（Hit@5 47.4%）→ bge 真实向量（52.6%）→ 检索四连优化（94.7%）→ 指标表核心块 + 股东信息锚定（100%）。完整实验报告见 `experiments/`。

## 技术栈

| 层 | 选型 |
|---|---|
| 后端 | Python 3.11 · FastAPI · uvicorn |
| PDF 解析 | pdfplumber / PyMuPDF |
| 切块 | 自实现结构感知切块（jieba 分词） |
| 检索 | sentence-transformers + bge-small-zh-v1.5（512 维）· FAISS · 自实现 BM25 · RRF |
| 重排 | FlagEmbedding + bge-reranker-v2-m3 |
| 生成 | DeepSeek（OpenAI 兼容接口，`deepseek-chat`） |
| 评估 | 自写 eval 框架 + RAGAS |
| 前端 | Next.js 16 · React 19 · TypeScript · Tailwind CSS 4 · shadcn/ui |

## 目录结构

```text
Financial-RAG-Agent/
├── backend/                    # Python RAG 后端
│   ├── api/                    # FastAPI 路由（chat / search / knowledge 知识库）
│   ├── src/                    # 核心源码
│   │   ├── ingestion/          # 巨潮下载 + PDF 解析（LayoutBlock）
│   │   ├── chunking/           # 结构感知切块
│   │   ├── retrieval/          # 稠密 / BM25 / RRF 融合 / 重排 / 金融增强
│   │   ├── generation/         # 生成 + 引用 + 数字校验 + 拒答
│   │   ├── agent/              # 金融问答 Agent
│   │   └── eval/               # golden set / 指标 / runner / RAGAS / 报告
│   ├── scripts/                # 一键脚本（下载/解析/切块/建索引/评估/API）
│   ├── tests/                  # pytest 单元测试
│   ├── config/                 # 全局配置（.env）
│   ├── data/                   # raw / parsed / corpus / index（gitignore）
│   ├── golden_set/             # 评估集（75 条真实 golden set）
│   ├── requirements.txt
│   └── .env.example
├── frontend/                   # FinFlow 金融研报 RAG 前端
│   ├── src/                    # 页面与组件（研报检索 / 图表检索 / 上传知识库）
│   ├── public/                 # 静态资源与 8 份真实年报 PDF
│   └── package.json
├── docs/                       # 规划与文档
├── experiments/                # 评估实验报告
└── README.md
```

## 快速开始

### 后端

```bash
cd backend
pip install -r requirements.txt

# 1. 配置 .env（复制 .env.example，配置 DeepSeek LLM Key 与本地 bge 模型路径）
cp .env.example .env

# 2. 下载真实年报（示例：贵州茅台 + 平安银行）
python scripts/download_reports.py --stocks 600519,000001 --categories ndbg,bndbg

# 3. 解析 → 切块 → 建索引
python scripts/parse_documents.py
python scripts/build_corpus.py
python scripts/index_corpus.py

# 4. 启动 API（http://127.0.0.1:8000）
python scripts/serve_api.py
```

> 无真实数据时可用演示数据跑通全链路：`python scripts/make_demo_data.py` + 上面的 3 步（指向 `demo_data/` 与 `corpus_demo/`）。

### 前端

```bash
cd frontend
pnpm install
node node_modules/next/dist/bin/next dev -p 5176   # http://127.0.0.1:5176
```

前端通过 `/api/finance/chat` 代理调用后端 `POST /api/chat`（默认 `http://127.0.0.1:8000`，可用环境变量 `FINANCE_BACKEND_URL` 覆盖）；后端不可用时自动回退内置 mock 演示。

## 核心配置（backend/.env）

| 配置 | 说明 |
|---|---|
| `EMBEDDING_PROVIDER` | `bge`（本地，推荐）/ `dashscope` / `hash`（占位演示） |
| `EMBEDDING_MODEL` | bge 模型路径（默认 `BAAI/bge-small-zh-v1.5`，可指向 ModelScope 本地目录） |
| `DASHSCOPE_API_KEY` | LLM Key（OpenAI 兼容；示例已配 DeepSeek key） |
| `DASHSCOPE_BASE_URL` | LLM 服务地址；DeepSeek 填 `https://api.deepseek.com/v1` |
| `LLM_MODEL` | 默认 `qwen-plus`；DeepSeek 填 `deepseek-chat` |
| `RERANK_BACKEND` | `auto`（默认）/ `bge` / `lexical` |
| `FINANCIAL_BOOST` | 指标表/股东信息锚定 pre-rerank 加权系数（默认 2.0） |
| `FINANCIAL_ANCHOR_BONUS` | 指标表核心块在重排阶段的加分（默认 0.10） |
| `RETRIEVAL_TOP_K / RETRIEVAL_FINAL_K` | 融合候选数 / 最终返回数 |
| `REFUSAL_THRESHOLD` | 拒答阈值 |
| `STRICT_NUMBERS` | 数字校验开关（默认 true） |

## API 概览

| 端点 | 说明 |
|---|---|
| `GET  /api/health` | 健康检查 |
| `POST /api/chat` | 金融问答（含引用 / 数字校验 / 拒答） |
| `POST /api/search` | 检索（返回命中片段） |
| `GET  /api/intent` | 意图识别 |
| `GET  /api/knowledge/files` | 知识库文件列表（真实语料） |
| `POST /api/knowledge/upload` | 上传 PDF（自动重建索引） |
| `DELETE /api/knowledge/files` | 删除语料文件 |
| `GET  /api/knowledge/file/{path}` | 语料 PDF 预览/下载 |

## 已知限制

1. **复杂版面 / 扫描件**：当前基线用 pdfplumber 解析；扫描件与复杂版面建议安装 MinerU / PaddleOCR PP-Structure（解析器已留好集成点）。
2. **索引重建耗时**：上传新文件后全量重建（解析 + bge 编码）约需 10 分钟，暂未做增量索引。
3. **数据规模**：当前语料为 2 家公司 8 份报告；golden set 75 条（项目规划 DoD 为 150 条）。
4. **DeepSeek 兼容**：RAGAS 的 `ResponseRelevancy` 需 `strictness=1` 且使用本地 bge 作 embeddings（已在 `src/eval/ragas_eval.py` 处理）。

## 相关文档

- [项目规划 docs/PROJECT_PLAN.md](docs/PROJECT_PLAN.md)
- [评估实验 experiments/](experiments/)
- [面试准备 docs/interview-prep-financial-rag-agent.md](docs/interview-prep-financial-rag-agent.md)
