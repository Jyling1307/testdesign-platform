"""LLM JSON 输出的 robust 解析（容忍代码块围栏、前后多余文本）。"""
import json


def parse_llm_json(text: str) -> dict:
    """解析 LLM 输出的 JSON。失败时抛 ValueError。"""
    text = (text or "").strip()
    # 去除 ```json ... ``` 围栏
    if text.startswith("```"):
        parts = text.split("```")
        if len(parts) >= 2:
            body = parts[1]
            if body.startswith("json"):
                body = body[4:]
            text = body.strip()
    # 截取首个 { 到末个 }
    start, end = text.find("{"), text.rfind("}")
    if start != -1 and end != -1 and end > start:
        text = text[start : end + 1]
    return json.loads(text)
