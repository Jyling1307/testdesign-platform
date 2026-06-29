# chroma_db 向量库（不入 Git）

本目录存放 ChromaDB 持久化数据（199063 节点知识库：4 仓库代码图谱 + 历史文档）。

**1.4GB，单文件最大 803MB，超 GitHub 100MB 限制，所以不入 Git。**

clone 后这个目录是空的，需要按下面方式恢复。

---

## 恢复方式（二选一）

### 方式 A：从网盘恢复（快，推荐）

1. 从网盘下载 `chroma_db_backup_*.tar.gz`（607MB）
2. 放到本目录的**上级**（`backend/data/`）
3. 解压（会自动创建 `chroma_db/` 并恢复全部数据）：

   ```bash
   cd backend/data
   tar -xzf chroma_db_backup_*.tar.gz
   ```

4. 启动后端验证：`python main.py` → 访问 `GET http://localhost:8000/api/knowledge/stats/` 看到 `knowledge_base: 199063` 即恢复成功

### 方式 B：从源数据全量重建（约 2 小时）

源数据已在仓库的 `backend/data/knowledge/`（历史文档 md/docx + 4 个仓库的代码图谱 JSON）。

```bash
cd backend
mkdir -p data/chroma_db

# 1. 入库历史文档（约 2 分钟，含 LLM 标签）
python -c "from rag.ingestion.ingest_service import ingest_directory; ingest_directory(reset=True)"

# 2. 入库代码图谱（约 2 小时，fast 模式）
python tools/ingest_code_graphs.py
```

详见项目根 `README.md` 的「知识库重建」章节。

---

## 目录结构（恢复后）

```
backend/data/chroma_db/
├── chroma.sqlite3              # 元数据库（534MB）
├── <uuid>/
│   └── data_level0.bin         # HNSW 向量索引（803MB）
└── ...其他 ChromaDB 内部文件
```
