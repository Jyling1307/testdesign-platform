"""Prompt template for refining test design based on user feedback."""

SYSTEM_PROMPT = """你是一位高级存储测试工程师，拥有多年企业存储产品（对象存储、文件存储、多协议网关、IDM等）的测试经验。用户正在审阅你生成的测试设计，并给出了反馈意见。

你的任务是：
1. 保持原有的三步结构（step1/step2/step3）
2. 根据用户的反馈修改对应的内容
3. 被标记为"已拒绝"的测试点需要根据反馈修改或删除
4. 新增用户要求的测试点
5. 输出完整的修改后文档（不要只输出diff）

step2 必须保持严格的5级缩进层级结构：
- 第1层：测试类型
- 第2层：用例标题
- 第3层：前置条件或操作步骤（不要写"操作""步骤"等标签）
- 第4层：预期结果
- 第5层：待确认（标注"需与开发确认"）

前置条件用简短陈述内嵌在操作前，如"目录下已有test.txt""已配置允许列表含.docx"。

格式规范：
- 使用4个空格缩进表示层级
- 每个层级用 `- ` 开头
- **不要**写"操作""步骤""预期"等标签词
- 不确定的标注"需与开发确认"
"""


def build_refine_prompt(current_md, rejected_nodes=None, feedback_text='', test_types=None):
    """Build prompt for test design refinement.

    Args:
        current_md: Current test design markdown
        rejected_nodes: List of rejected node paths and texts
        feedback_text: User's natural language feedback
        test_types: List of test types to include

    Returns:
        tuple: (system_prompt, user_message)
    """
    user_message = f"""## 当前测试设计

{current_md}
"""

    if rejected_nodes:
        user_message += "\n## 被拒绝/需修改的测试点\n\n"
        for node in rejected_nodes:
            fb = node.get('feedback', '')
            line = f"- {node.get('node_text', '')}"
            if fb:
                line += f"（修改建议：{fb}）"
            user_message += line + "\n"

    if feedback_text:
        user_message += f"""
## 修改意见

{feedback_text}
"""

    if test_types:
        user_message += f"""
## 测试类型范围

本次仅保留以下测试类型：{', '.join(test_types)}
"""

    user_message += '\n请根据以上反馈，输出修改后的完整测试设计文档。保持5级缩进层级结构，不要写"操作""步骤"等标签前缀。\n'

    return SYSTEM_PROMPT, user_message
