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
| `EMBEDDING_PROVIDER` | `dashscope`（推荐）/ `bge`（本地）/ `hash`（占位演示） |
| `DASHSCOPE_API_KEY` | 阿里云 Dashscope Key（embedding + LLM 共用） |
| `LLM_MODEL` | 默认 `qwen-plus` |
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

## 已知限制与后续优化

1. **LLM 需配置可用 Key**：本机 Dashscope 免费额度耗尽，生成评估走了占位回答；
   配置可用 Key 后数字校验/RAGAS 才有真实意义。
2. **重排默认词法兜底**：安装 `FlagEmbedding` + bge-reranker 模型后自动升级为交叉编码器重排。
3. **真实 PDF 复杂场景**：扫描件/复杂版面建议安装 MinerU / PaddleOCR PP-Structure（解析器已留好集成点）。
4. **Embedding 批量上限 10**：代码已按 Dashscope 限制处理，换其他服务商请调整 `embedding.py` 的 BATCH。

## 技术栈

Python 3.11 · pdfplumber/PyMuPDF · reportlab（演示） · FAISS · jieba（自实现 BM25）·
RRF · bge-reranker（可选） · OpenAI 兼容接口 · FastAPI · RAGAS（可选）
