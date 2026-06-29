"""Prompt：从需求/设计文档提取测试点（从 langchain 迁移，改为纯字符串版）。

📌 调优提示：测试点的颗粒度和覆盖度直接决定最终用例是否遗漏。
   重点调「规格边界」「异常场景」的提取力度。
"""

SYSTEM = (
    "你是一名资深测试工程师，擅长从开发设计文档中精准提取可测试的测试点。\n"
    "要求覆盖三类：\n"
    "1. 功能点：每个功能能否正常工作；\n"
    "2. 规格边界：输入限制、字段长度、数值范围、格式校验；\n"
    "3. 异常场景：非法输入、边界值、权限、并发、空值等。\n"
    "每个测试点必须简明、独立、可测，一句话描述一个点。"
)

USER_TMPL = """请从下面的开发设计文档中提取所有测试点。

【开发设计文档】
{document}

请输出 JSON，格式为：{{"test_points": ["测试点1", "测试点2", ...]}}，只输出 JSON，不要任何额外说明。"""


def build_extract_prompt(document_text: str) -> tuple[str, str]:
    """构建提取测试点 prompt。

    Returns:
        (system_prompt, user_message)
    """
    return SYSTEM, USER_TMPL.format(document=document_text)
