"""Q2E 查询扩展（★批量优化版，从 langchain 迁移）。

🚀 核心优化：langchain 原版是串行 for 循环（每个测试点调 1 次 LLM，N 个点 = N 次调用），
   这里改为批量版——所有测试点打包 1 次 LLM 调用，速度提升 10 倍+。

借鉴第 12 讲 multi-query 思路：把每个测试点扩写成多个独立检索问题，
覆盖正常/异常/边界三类，提高从历史知识库召回相关内容的概率。
"""
from rag.common.parse import parse_llm_json
from rag.config import LLMConfig, RAGConfig


def batch_expand_queries(test_points: list[str], count_per_tp: int | None = None) -> list[str]:
    """所有测试点打包，1 次 LLM 调用生成全部检索问题。

    Args:
        test_points: 测试点列表
        count_per_tp: 每个测试点扩写几个问题（默认 RAGConfig.Q2E_QUESTION_COUNT）

    Returns:
        去重保序的检索问题列表

    🚀 这是 langchain 慢的根因修复：从 N 次串行 LLM 调用 → 1 次批量调用。
    """
    if not test_points:
        return []

    count = count_per_tp or RAGConfig.Q2E_QUESTION_COUNT
    from llm.prompts.q2e_expand import build_batch_expand_prompt
    from llm.client import chat

    system, user = build_batch_expand_prompt(test_points, count)
    try:
        raw = chat(system, user, temperature=LLMConfig.get_temperature("expand"))
        questions = parse_llm_json(raw).get("questions", [])
    except Exception:  # noqa: BLE001 解析失败回退：直接用测试点做 query
        questions = list(test_points)

    # 去重保序
    seen: set[str] = set()
    result: list[str] = []
    for q in questions:
        q = q.strip()
        if q and q not in seen:
            seen.add(q)
            result.append(q)
    return result


def expand_test_points(test_points: list[str]) -> list[str]:
    """兼容 langchain 旧接口的包装函数（内部走批量版）。"""
    return batch_expand_queries(test_points)
