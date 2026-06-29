"""Prompt：Q2E 测试点批量扩写成检索问题（★批量优化版）。

🚀 核心优化：一次接收所有测试点，输出全部检索问题。
   langchain 原版是逐个扩写（N 次 LLM 调用，慢的根因），
   这里改为批量（1 次 LLM 调用），速度提升 10 倍+。

借鉴第 12 讲 multi-query 思路：每个测试点扩写成多个独立检索问题，
覆盖正常/异常/边界三类，提高从历史知识库召回相关内容的概率。
"""

SYSTEM = (
    "你是测试知识库检索助手。任务是把多个测试点扩写成独立的检索问题，"
    "用于从历史测试设计/代码图谱中召回高相关内容。\n"
    "扩写要求：每个测试点覆盖【正常流程】【异常场景】【边界条件】三类，"
    "问题要像真实会去检索的问句。"
)

USER_TMPL = """请把下面的每个测试点各扩写成 {count} 个检索问题。

【测试点列表】
{test_points}

请输出 JSON，格式为：
{{"questions": ["问题1", "问题2", ...]}}

要求：
1. 每个测试点都要扩写出 {count} 个问题，合并到一个 questions 数组；
2. 问题要独立、可检索、覆盖正常/异常/边界三类；
3. 只输出 JSON，不要任何额外说明。"""


def build_batch_expand_prompt(test_points: list[str], count: int) -> tuple[str, str]:
    """构建批量扩写 prompt。

    Args:
        test_points: 所有测试点列表
        count: 每个测试点扩写几个问题

    Returns:
        (system_prompt, user_message)
    """
    tp_text = "\n".join(f"{i + 1}. {tp}" for i, tp in enumerate(test_points))
    return SYSTEM, USER_TMPL.format(test_points=tp_text, count=count)
