"""轻量 pipeline 编排（从 langchain 迁移，适配 FastAPI + 流式优化）。

4 步流程：提取测试点 → Q2E 批量扩写 → 多源检索 + few-shot → 流式生成测试设计 md。

🚀 核心优化（vs langchain 原版）：
- 批量 Q2E：1 次 LLM 替代 N 次串行调用
- 流式生成：配合 WebSocket 实时输出
- 总 LLM 调用：3 次（extract + expand + generate），langchain 原版 N+2 次
"""
from typing import AsyncIterator

from rag.common.parse import parse_llm_json
from rag.config import LLMConfig
from rag.retrieval.query_expander import batch_expand_queries
from rag.retrieval.retriever import RAGRetriever
from rag.retrieval.few_shot_selector import select_few_shot


# ============================================================
# 步骤1：提取测试点
# ============================================================
def extract_test_points(document_text: str) -> list[str]:
    """LLM 提取测试点（结构化 JSON 输出）。"""
    from llm.prompts.extract_testpoints import build_extract_prompt
    from llm.client import chat

    system, user = build_extract_prompt(document_text)
    try:
        raw = chat(system, user, temperature=LLMConfig.get_temperature("extract"))
        return parse_llm_json(raw).get("test_points", [])
    except Exception:  # noqa: BLE001 解析失败返回空
        return []


# ============================================================
# 步骤2：Q2E 批量扩写（直接复用 rag.retrieval.query_expander）
# ============================================================
def expand_to_queries(test_points: list[str]) -> list[str]:
    """测试点 → 去重后的检索问题列表（批量扩写，1 次 LLM）。"""
    return batch_expand_queries(test_points)


# ============================================================
# 步骤3：多源检索 + rerank + few-shot 精选
# ============================================================
def retrieve_context(queries: list[str], source_types: list[str] | None = None) -> dict:
    """检索上下文 + few-shot 示例。"""
    retriever = RAGRetriever()
    results = retriever.retrieve(queries, source_types=source_types)

    context_text = "\n\n---\n\n".join(
        f"[来源:{m.get('source_type', '')} | {m.get('module_path', '')}]\n{doc}"
        for doc, _score, m in results
    )
    few_shot = select_few_shot(queries[0] if queries else "")
    few_shot_text = "\n\n---\n\n".join(few_shot)

    return {"context": context_text, "few_shot": few_shot_text, "raw": results}


# ============================================================
# 步骤4：生成测试设计 md（非流式 / 流式 两个版本）
# ============================================================
def _build_final_user_message(
    document_text: str, context: str, few_shot: str,
    test_points: list[str], notes: str = "", test_types=None,
) -> tuple[str, str]:
    """构建生成步骤的完整 prompt（复用 testdesign 现有 build_generate_prompt）。"""
    from llm.prompts.generate_design import build_generate_prompt

    system, user = build_generate_prompt(
        document_text, kb_context=context, user_notes=notes, test_types=test_types
    )
    # 追加已提取的测试点（让 LLM 知道要覆盖哪些点）
    tp_text = "\n".join(f"- {tp}" for tp in test_points)
    user += f"\n\n## 已提取的测试点（必须全部覆盖）\n{tp_text}\n"
    if few_shot:
        user += f"\n## 参考历史用例风格（few-shot，模仿但不要照搬）\n{few_shot}\n"
    return system, user


def generate_design_md(
    test_points: list[str], context: str, few_shot: str,
    document_text: str = "", notes: str = "", test_types=None,
) -> str:
    """非流式生成完整测试设计 md。"""
    from llm.client import chat

    system, user = _build_final_user_message(
        document_text, context, few_shot, test_points, notes, test_types
    )
    return chat(system, user, temperature=LLMConfig.get_temperature("generate"))


async def stream_generate_design_md(
    test_points: list[str], context: str, few_shot: str,
    document_text: str = "", notes: str = "", test_types=None,
) -> AsyncIterator[str]:
    """异步流式生成测试设计 md，yield 文本块（配合 WebSocket）。"""
    from llm.client import stream_chat

    system, user = _build_final_user_message(
        document_text, context, few_shot, test_points, notes, test_types
    )
    async for chunk in stream_chat(
        system, user, temperature=LLMConfig.get_temperature("generate")
    ):
        yield chunk


# ============================================================
# 端到端编排（非流式版，调试用）
# ============================================================
def run_pipeline(document_text: str, source_types: list[str] | None = None) -> dict:
    """端到端跑通（非流式），返回各步产物（便于回溯调试）。"""
    test_points = extract_test_points(document_text)
    queries = expand_to_queries(test_points)
    retrieved = retrieve_context(queries, source_types=source_types)
    design_md = generate_design_md(
        test_points, retrieved["context"], retrieved["few_shot"], document_text
    )
    return {
        "test_points": test_points,
        "expanded_queries": queries,
        "retrieved_context": retrieved["raw"],
        "design_md": design_md,
    }
