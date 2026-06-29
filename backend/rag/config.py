"""RAG 配置中心（从 langchain 迁移 + FastAPI 适配）。

📌 这是玲玲大人 RAG/LLM 调优的总入口。
   所有可调参数集中在本文件，改一处全局生效。

连接信息（base_url / api_key / model）从 config.settings（.env）读取；
推理参数（温度、top_k、chunk 大小等）在这里直接定义。
"""
from config import settings


# ============================================================
# 生成模型（智谱 GLM，Anthropic 兼容接口，比 langchain 的 OpenAI 接口更快）
# ============================================================
class LLMConfig:
    base_url = settings.LLM_BASE_URL
    api_key = settings.LLM_API_KEY
    model = settings.LLM_MODEL

    # ⭐ 按用途设温度：提取要稳、扩写适中、生成要贴合风格但允许措辞变化
    TEMPERATURES = {
        "extract": 0.1,   # 提取测试点（结构化输出，越稳越好）
        "expand": 0.3,    # Q2E 扩写检索问题（适度发散）
        "generate": 0.5,  # 生成测试设计（贴合风格，允许措辞差异）
        "tag": 0.1,       # 标签提取（结构化）
        "default": 0.3,
    }
    MAX_TOKENS = 4096
    REQUEST_TIMEOUT = 120  # 秒

    @classmethod
    def get_temperature(cls, purpose: str) -> float:
        return cls.TEMPERATURES.get(purpose, cls.TEMPERATURES["default"])


# ============================================================
# Reranker（硅基流动 rerank API，与 embedding 同账号）
# ============================================================
class RerankerConfig:
    base_url = settings.EMBEDDING_BASE_URL  # 复用 embedding 的硅基流动地址
    api_key = settings.EMBEDDING_API_KEY
    model = settings.RERANK_MODEL
    top_n = 5  # ⭐ rerank 后保留数量（调优重点）
    timeout = 60  # 请求超时（秒）


# ============================================================
# ⭐ RAG 检索/切分调参（集中在这里方便玲玲大人对照调）
# ============================================================
class RAGConfig:
    # ---- 层级切分（父子三级，借鉴 langchain 04/15 讲）----
    LEVEL_MODULE = "module"   # 功能模块（父，回溯上下文用）
    LEVEL_FEATURE = "feature"  # 核心功能点（中）
    LEVEL_SPEC = "spec"       # 规格边界（叶子，建向量索引、用于检索）

    CHUNK_SIZES = [1500, 400, 100]  # ⭐ 父/中/叶 token 上限
    OVERLAP_RATIO = 0.15            # ⭐ 超长块滑动窗口重叠比例（建议 10-20%）
    MAX_CHUNK_TOKENS = 500          # 超过此值触发二次切分

    # ---- 检索 ----
    SIMILARITY_TOP_K = 8   # ⭐ 每个问题召回数量
    RERANK_TOP_N = 5       # ⭐ rerank 后保留
    Q2E_QUESTION_COUNT = 5  # ⭐ 每个测试点扩写成几个检索问题
    FEW_SHOT_COUNT = 3     # ⭐ few-shot 历史用例条数（学风格）

    # ---- Chroma collection（单一 collection，父子同库，metadata 区分 level）----
    COLLECTION = "knowledge_base"

    # ---- 标签增强开关（入库时给 feature 节点打 LLM 标签）----
    TAGGER_ENABLED = True

    # ---- 混合检索（第一版预留，默认只跑稠密向量）----
    USE_HYBRID = False
    BM25_ALPHA = 0.3
