# Financial-RAG-Agent

面向 A 股上市公司**年报 / 半年报 / 公告**的垂直金融 RAG 系统，全部由 Python 实现。

从 0 到 1 搭建：复杂 PDF 解析（表格 / 多栏 / 扫描件 OCR）→ 结构感知切块 →
BM25 + 稠密混合检索 + 重排 → 生成（引用溯源 / 数字校验 / 拒答），
并用 golden set + 量化指标（Hit@k / MRR / NDCG / RAGAS）证明每一层优化的价值。

> 完整规划见 [docs/PROJECT_PLAN.md](docs/PROJECT_PLAN.md)

## 数据流

```
巨潮 PDF ─▶ 解析(LayoutBlock) ─▶ 结构感知切块 ─▶ 索引(稠密+BM25)
                                                  │
用户问题 ─▶ 混合检索(RRF) ─▶ 重排 ─▶ 生成(引用/数字校验/拒答) ─▶ 回答
                                                  │
                            golden set + Hit@k/MRR/RAGAS 评估闭环
```

## 快速开始（演示数据，零外部依赖跑通全链路）

```bash
pip install -r requirements.txt

# 1. 生成 4 份"示例科技"演示 PDF + 8 条 golden set
python scripts/make_demo_data.py

# 2. 解析 → 切块 → 建索引（默认写入 data/parsed, data/corpus, data/index）
python scripts/parse_documents.py --source demo_data/raw --out data/parsed_demo
python scripts/build_corpus.py --source data/parsed_demo --out data/corpus/chunks.json
python scripts/index_corpus.py --chunks data/corpus/chunks.json --index data/index

# 3. 评估（检索指标 + dense-only A/B 对照 + 生成评估）
python scripts/run_eval.py --golden golden_set/demo_golden_set.csv --index data/index --chunks data/corpus/chunks.json --gen

# 4. 启动 API（http://127.0.0.1:8000）
python scripts/serve_api.py
#   POST /api/chat   {"question": "示例科技2023年的毛利率是多少？"}
#   POST /api/search {"question": "...", "top_k": 5}
```

演示数据实测结果（8 条 golden set）：HitRate@3 = 100%，HitRate@5 = 100%，MRR = 83.3%，见 `experiments/examples/`。

## 真实数据流程（巨潮资讯网）

```bash
# 1. 下载年报/半年报（见 stocks.example.txt）
python scripts/download_reports.py --stock-file stocks.example.txt --categories ndbg,bndbg

# 2~4. 解析 → 切块 → 建索引
python scripts/parse_documents.py
python scripts/build_corpus.py
python scripts/index_corpus.py

# 5. 生成 golden set 草稿（LLM 出题 + 人工校验）
python scripts/build_golden_set.py --n 50

# 6. 评估
python scripts/run_eval.py --gen
```

## 核心配置（.env）

| 配置 | 说明 |
|---|---|
| `EMBEDDING_PROVIDER` | `bge`（本地，推荐）/ `dashscope` / `hash`（占位演示） |
| `DASHSCOPE_API_KEY` | LLM Key（OpenAI 兼容；本机已配 DeepSeek key） |
| `DASHSCOPE_BASE_URL` | LLM 服务地址，默认阿里云；DeepSeek 填 `https://api.deepseek.com/v1` |
| `LLM_MODEL` | 默认 `qwen-plus`；DeepSeek 填 `deepseek-chat` |
| `RERANK_ENABLED` | 重排开关（默认 true；装 FlagEmbedding 后自动用 bge-reranker） |
| `RETRIEVAL_TOP_K / FINAL_K` | 融合候选数 / 最终返回数 |
| `FUSION` | `rrf`（默认）/ `weighted` |
| `REFUSAL_THRESHOLD` | 拒答阈值 |
| `STRICT_NUMBERS` | 数字校验开关（默认 true） |

## 项目结构

```
├── data/            # raw/parsed/corpus/index（gitignore）
├── demo_data/       # 演示 PDF（make_demo_data.py 生成，gitignore）
├── golden_set/      # golden set 规范 + 标注数据
├── experiments/     # 实验记录 + 评估报告
├── scripts/         # 一键脚本（下载/解析/切块/建索引/评估/出题/API）
├── src/
│   ├── ingestion/   # 下载器 + 解析器(LayoutBlock) + OCR
│   ├── chunking/    # 结构感知切块
│   ├── retrieval/   # 稠密/BM25/RRF融合/重排/金融增强
│   ├── generation/  # 生成 + 引用 + 数字校验 + 拒答
│   ├── agent/       # 金融问答 Agent + 计算工具
│   └── eval/        # golden set / 指标 / runner / RAGAS / 报告
├── api/             # FastAPI 服务
└── config/          # 全局配置
```

## 当前进度

- [x] W1 数据下载（巨潮资讯网）
- [x] W2 文档解析（表格/版面/OCR 分层）
- [x] W3 结构感知切块
- [x] W4 混合检索 + 重排 + 金融增强
- [x] W5 评估体系（golden set + Hit@k/MRR/NDCG + A/B + RAGAS）
- [x] W6 金融 Agent + API
- [x] 真实数据链路（2026-09-01）：巨潮下载 8 份真实年报/半年报（贵州茅台 600519 + 平安银行 000001，2022~2024）
- [x] 本地 bge 向量（bge-small-zh-v1.5，512 维，ModelScope 下载），真实语义稠密检索
- [x] 真实 golden set（22 条，覆盖 fact/table/calc/compare/multi_doc/reject 六类，证据可溯源）
- [x] 真实评估：Hit@5=94.7% MRR=58.9%（hash 47.4%/23.4% → bge 52.6%/30.9% → 检索优化后 94.7%/58.9%）；DeepSeek 生成拒答 100%、数字校验通过率 78.9%+
- [x] 检索优化：候选池放大、财务章节锚定加权、元数据增强检索文本、重排兜底改增强文本、股票代码→公司名映射
- [ ] 剩余短板：茅台2023营收单个样本仍命中审计段落（19 样本中 1 例）

## 已知限制与后续优化

1. **LLM 已配置 DeepSeek**：`backend/.env` 使用 `DASHSCOPE_BASE_URL=https://api.deepseek.com/v1` + `LLM_MODEL=deepseek-chat`（OpenAI 兼容接口，变量名沿用历史命名）；
   真实问答已验证：引用溯源 + 数字校验（已支持万元/亿元/百万元单位换算匹配）+ 拒答可用，数字校验通过率 78.9%，剩余误报来自回答中的解释性数字。
2. **重排默认词法兜底**：安装 `FlagEmbedding` + bge-reranker 模型后自动升级为交叉编码器重排。
3. **真实数据检索定位**：财务数字问答常命中审计「收入确认」政策段落而非「主要会计数据」表，
   已通过元数据增强/章节锚定/候选池放大优化至 Hit@5=94.7%、MRR=58.9%；剩余个别样本（如茅台2023营收）仍命中审计政策段落，可用真实重排器（bge-reranker）或查询改写进一步收敛。
4. **真实 PDF 复杂场景**：扫描件/复杂版面建议安装 MinerU / PaddleOCR PP-Structure（解析器已留好集成点）。

## 技术栈

Python 3.11 · pdfplumber/PyMuPDF · reportlab（演示） · FAISS · jieba（自实现 BM25）·
RRF · bge-reranker（可选） · OpenAI 兼容接口 · FastAPI · RAGAS（可选）


## 项目结构（参考 AI_Agent_Assistant_System 的 backend/frontend 布局）

```text
Financial-RAG-Agent/
├── backend/                    # Python RAG 后端（FastAPI）
│   ├── api/                    # API 路由（/api/chat, /api/search）
│   ├── src/                    # 核心源码（解析/切块/索引/检索/生成）
│   ├── scripts/                # 一键脚本（建数据/建索引/评估/启动 API）
│   ├── config/                 # 配置
│   ├── data/                   # 解析结果/语料/索引
│   ├── demo_data/              # 演示 PDF
│   ├── golden_set/             # 评估集
│   ├── logs/                   # 运行日志
│   ├── requirements.txt
│   └── .env.example
├── frontend/                   # FinFlow 金融研报 RAG 前端（Next.js 16 + shadcn/ui）
│   ├── src/                    # 页面与组件（研报检索 / 图表检索 / 上传知识库）
│   ├── public/                 # 静态资源与 mock 数据
│   ├── package.json
│   └── pnpm-workspace.yaml
├── docs/                       # 规划文档
├── experiments/                # 评估实验结果
└── README.md
```

> 前端启动：`cd frontend && pnpm install && pnpm dev`（或 `node node_modules/next/dist/bin/next dev -p 5176`）
> 后端启动：`cd backend && python scripts/serve_api.py`

## 前端 ↔ 后端联调（FinFlow → Financial-RAG-Agent）

- 前端通过 `frontend/src/app/api/finance/chat/route.ts` 代理调用后端 `POST /api/chat`（默认 http://127.0.0.1:8000，可用环境变量 `FINANCE_BACKEND_URL` 覆盖）。
- 后端不可用时前端自动回退到内置 mock 演示，不会白屏。
- 本地开发：后端 `cd backend && python scripts/serve_api.py`，前端 `cd frontend && node node_modules/next/dist/bin/next dev -p 5176`。
- GitHub Pages 静态导出仍可用：构建时设置 `NEXT_PUBLIC_STATIC_EXPORT=true`（此时 basePath=/KnowFlow，API 代理在静态托管下不可用，仅演示 UI）。
