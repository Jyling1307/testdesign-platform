# TestDesignAI Platform

测试用例智能生成平台：上传开发设计文档 → 4 步 RAG pipeline → 生成结构化测试设计 Markdown → 思维导图审核 → 转 xlsx 测试用例。

## 技术栈

- 后端：FastAPI + SQLAlchemy + ChromaDB + LangChain（ChatAnthropic）
- 前端：Vue3 + Vite + Pinia + Vue Router
- LLM：智谱 GLM-5-turbo（Anthropic 兼容接口）
- Embedding：硅基流动 bge-m3
- Rerank：硅基流动 bge-reranker-v2-m3

## RAG 4 步 Pipeline

```
[入库 - 离线一次性]
  docx/md/json → ChunkNode → 术语标准化 → feature/spec 切分 → LLM标签 → embedding → ChromaDB

[生成 - 在线 4 步]
  ① 提取测试点（1次LLM）→ ② 批量扩写检索问题（1次LLM★）→ ③ 多源检索+few-shot（1次LLM）→ ④ 流式生成测试设计（1次LLM）
  总计 4 次 LLM 调用（vs langchain 原方案 N+2 ≈ 22 次）
```

**核心优化**：批量 Q2E——把 langchain 的"N 个测试点串行 N 次 LLM 调用"改为"1 次批量调用"，速度提升 10 倍+。

## 快速开始

### 1. 后端

```bash
cd backend
python -m venv venv
source venv/Scripts/activate   # Windows git bash
pip install -r requirements.txt

cp .env.example .env           # 填入真实 API key
python main.py                 # http://localhost:8000
```

### 2. 前端

```bash
cd frontend
npm install
npm run dev                    # http://localhost:5173
```

## 知识库重建

知识库向量库（chroma_db，1.4GB）不入 Git，两种重建方式：

### 方式 A：从压缩包恢复（快，推荐）

从网盘下载 `chroma_db_backup_*.tar.gz`，解压到 `backend/data/chroma_db/`：

```bash
cd backend/data
tar -xzf chroma_db_backup_20260629.tar.gz
```

启动后端即可使用（已含 199063 节点：4 仓库代码图谱 + 历史文档）。

### 方式 B：从源数据全量重建（约 2 小时）

源数据已包含在仓库的 `backend/data/knowledge/`：
- 历史测试设计 md（3 份）
- 历史开发设计 docx（3 份）
- 代码图谱 JSON（v3/v5/mos_v6/om 四个仓库，AST 扫描生成）

```bash
cd backend
python -c "
from rag.ingestion.ingest_service import ingest_directory
ingest_directory(reset=True)                       # 入库历史文档（约 2 分钟，含 tagger）
"
python tools/ingest_code_graphs.py                 # 入库代码图谱（约 2 小时，fast 模式）
```

重新生成代码图谱（仓库更新后）：

```bash
python tools/code_graph_scanner.py                 # 扫描 4 个自动化仓库生成 JSON
```

## 项目结构

```
backend/
├── rag/                        # ★ RAG 核心模块（从 langchain 迁移）
│   ├── config.py               #   RAGConfig + LLMConfig + RerankerConfig（调参总入口）
│   ├── common/                 #   ChunkNode 数据结构 + parse_llm_json
│   ├── ingestion/              #   入库：parsers(glossary/splitter/tagger/indexer)
│   ├── retrieval/              #   检索：query_expander(批量★)/retriever/few_shot/reranker
│   └── pipeline/orchestrator.py#   4 步编排
├── llm/                        # LLM 客户端 + prompts
├── knowledge/                  # ChromaDB 服务 + embedding
├── websocket/                  # WebSocket 流式生成（4 步 pipeline 入口）
├── routers/                    # FastAPI 路由（含知识库管理 API）
├── tools/                      # ★ 工具脚本
│   ├── code_graph_scanner.py   #   AST 扫描仓库生成代码图谱 JSON
│   ├── ingest_code_graphs.py   #   fast 模式批量入库代码图谱
│   └── rag_demo.py             #   RAG 流程演示（可视化每步输出）
├── data/
│   ├── knowledge/              #   历史文档 + 代码图谱 JSON（重建源数据）
│   └── glossary/               #   术语词库（可选）
└── config.py                   # 全局配置
frontend/                       # Vue3 前端
```

## 关键配置

- `backend/rag/config.py`：RAG 调参总入口（chunk 大小、top_k、Q2E 问题数、few-shot 数、tagger 开关）
- `backend/.env`：API key（参考 `.env.example`）

## 知识库管理 API

| 端点 | 功能 |
|---|---|
| `POST /api/knowledge/ingest-directory/` | 批量入库目录（docx/md/json） |
| `POST /api/knowledge/ingest-code-graph/` | 上传代码图谱 JSON |
| `GET /api/knowledge/stats/` | 各 collection 节点数统计 |
| `POST /api/knowledge/reset/` | 清空 knowledge_base collection |
| `POST /api/knowledge/search/` | 语义搜索（前端用） |

## RAG 流程演示

```bash
cd backend
python tools/rag_demo.py                 # 内置示例
python tools/rag_demo.py design.txt      # 指定文档
```

会逐步打印：提取测试点 → 扩写检索问题 → 检索上下文 → 流式生成，每步含耗时与输出明细。

## 备注

- 向量库 `chroma_db/` 不入 Git（单文件最大 803MB，超 GitHub 100MB 限制），走网盘传输
- `.env` 不入 Git（含 API key），参考 `.env.example` 配置
