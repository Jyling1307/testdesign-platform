"""Prompt template for knowledge-base Q&A (检索增强问答).

检索完成后，把片段作为 context，让 LLM 综合解读用户问题。
用于 /api/knowledge/ask/ SSE 接口。
"""

SYSTEM_PROMPT = """你是知识库问答助手，擅长存储产品领域（对象存储、文件存储、多协议网关、IDM 等）。

你的任务：基于「知识库片段」回答用户的检索问题。回答要求：
- **忠于片段**：只基于提供的片段内容回答，不要编造片段里没有的信息。
- **标注来源**：引用关键结论时，用【片段N】标注出处，方便用户核对。
- **区分来源类型**：片段分「设计文档」「测试用例」「代码图谱」三类，代码图谱说明的是接口/调用关系，设计文档说明的是规格/方案，回答时注意区分语境。
- **片段不足时**：直接说明"知识库中未找到 XXX 相关内容"，不要硬凑。
- **结构清晰**：用简短的分点或小标题组织，避免大段堆砌。

回答风格：专业、简洁、可直接用于工作汇报。"""


def build_answer_prompt(question: str, snippets: list[dict]) -> str:
    """构建 user prompt：问题 + 检索片段。

    Args:
        question: 用户原始问题
        snippets: 检索片段列表，每项形如 {content, source, source_type, heading, collection}
    """
    if not snippets:
        return f"问题：{question}\n\n（知识库未检索到任何相关片段，请直接告知用户未找到相关内容。）"

    parts = [f"问题：{question}\n", "知识库片段："]
    type_label = {
        'code': '代码图谱',
        'design_doc': '设计文档',
        'test_design': '测试设计',
        'document': '设计文档',
        'testcase': '测试用例',
    }
    for i, s in enumerate(snippets, 1):
        stype = type_label.get(s.get('source_type', ''), s.get('source_type', ''))
        source = s.get('source') or ''
        heading = s.get('heading') or ''
        content = s.get('content') or ''
        header = f"【片段{i}】[{stype}]"
        if source:
            header += f" 来源：{source}"
        if heading:
            header += f" / {heading}"
        parts.append(f"{header}\n{content}")
    parts.append("\n请基于以上片段回答问题。")
    return "\n\n".join(parts)
