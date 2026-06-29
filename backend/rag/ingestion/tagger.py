"""标签增强检索（从 langchain 迁移，适配 FastAPI 的 llm.client）。

给 chunk 打结构化标签（功能模块 / 测试类型 / 优先级），检索时 query 也提标签做过滤，
提升召回精准度（先标签命中、再向量匹配）。

策略：只对 feature（父）节点用 LLM 打标签（节点少、成本可控），
spec（叶子）继承父 feature 的标签。
"""
from rag.common.chunk import ChunkNode
from rag.common.parse import parse_llm_json
from rag.config import LLMConfig

TAG_SYSTEM = "你从文档片段中提取结构化测试标签，用于检索过滤。判断不出就留空字符串。"

TAG_USER_TMPL = """请从以下文档片段提取测试相关标签：
{content}

输出 JSON：{{"module": "功能模块名（如登录/支付/订单，没有则空）", "test_type": "功能/边界/异常/性能/安全 之一，判断不出则空", "priority": "P0/P1/P2 或空"}}
只输出 JSON。"""


def tag_content(content: str) -> dict:
    """用 LLM 提取内容的结构化标签。

    LLM 不可用（余额不足/限流）时降级返回空标签，不阻塞入库与检索主流程。
    """
    try:
        from llm.client import chat
        raw = chat(
            TAG_SYSTEM,
            TAG_USER_TMPL.format(content=content[:1500]),
            temperature=LLMConfig.get_temperature("tag"),
        )
        tags = parse_llm_json(raw)
        return {k: str(v).strip() for k, v in tags.items()}
    except Exception:  # noqa: BLE001 LLM 调用或解析失败，降级返回空标签
        return {}


def tag_nodes(nodes: list[ChunkNode]) -> None:
    """给 feature 节点打标签，spec 叶子继承父 feature 标签。原地修改。"""
    feature_tags: dict[str, dict] = {}
    for n in nodes:
        if not n.parent_id:  # feature / 顶层节点
            tags = tag_content(n.content)
            n.extra["tags"] = tags
            feature_tags[n.id] = tags
    # spec 叶子继承父 feature 标签
    for n in nodes:
        if n.parent_id and n.parent_id in feature_tags and "tags" not in n.extra:
            n.extra["tags"] = feature_tags[n.parent_id]
