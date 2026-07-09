"""术语标准化（从 langchain 迁移）。

词库格式（放 data/glossary/*.json，可多文件合并）：
{
  "登录": {"synonyms": ["登陆", "log in", "login"], "definition": "用户身份验证入口"},
  ...
}
"""
import json
import re
from functools import lru_cache
from pathlib import Path

from config import DATA_DIR


def _glossary_dir() -> Path:
    return Path(DATA_DIR) / "glossary"


@lru_cache(maxsize=1)
def load_glossary() -> dict:
    """加载 data/glossary/ 下所有词库 JSON 并合并。"""
    glossary_dir = _glossary_dir()
    if not glossary_dir.exists():
        return {}
    merged: dict = {}
    for f in glossary_dir.glob("*.json"):
        with open(f, "r", encoding="utf-8") as fp:
            data = json.load(fp)
        merged.update(data)
    return merged


@lru_cache(maxsize=1)
def _alias_map() -> dict:
    """{别名小写: [标准术语...]}，按长度降序（优先匹配长词）。"""
    amap: dict[str, list[str]] = {}
    for term, info in load_glossary().items():
        aliases = [term] + list((info or {}).get("synonyms", []))
        for alias in aliases:
            amap.setdefault(alias.lower(), []).append(term)
    return dict(sorted(amap.items(), key=lambda x: len(x[0]), reverse=True))


def standardize(text: str) -> str:
    """把文本中的同义词替换为标准术语。"""
    amap = _alias_map()
    if not amap or not text:
        return text
    result = text
    for alias_lower, terms in amap.items():
        standard = terms[0]
        if re.search(r"[a-zA-Z]", alias_lower):
            pattern = re.compile(
                r"(?<![a-zA-Z])" + re.escape(alias_lower) + r"(?![a-zA-Z])", re.IGNORECASE
            )
        else:
            pattern = re.compile(re.escape(alias_lower))
        result = pattern.sub(lambda _m: standard, result)
    return result


def extract_terms(text: str) -> list[str]:
    """从文本中提取命中的标准术语（用于 metadata 过滤召回）。"""
    amap = _alias_map()
    if not amap or not text:
        return []
    found: set[str] = set()
    lower = text.lower()
    for alias_lower, terms in amap.items():
        if alias_lower in lower:
            found.update(terms)
    return sorted(found)


def expand_query(text: str) -> str:
    """检索查询扩展：把中文术语追加其英文同义词，提升中英跨语言召回。

    与 standardize（入库用，把英文统一成中文标准术语）相反，
    expand_query 用于检索前，把"桶配额"扩成"桶配额 bucket quota"，
    让 embedding 能同时匹配中文文档和英文代码符号。

    优先匹配长 key（避免"桶配额"被"桶"和"配额"拆开重复追加）。
    """
    glossary = load_glossary()
    if not glossary or not text:
        return text

    # 按 key 长度降序，优先匹配长术语（如"存储池"优先于"池"）
    sorted_keys = sorted(glossary.keys(), key=len, reverse=True)
    extras: list[str] = []
    seen: set[str] = set()
    consumed_spans: list[tuple[int, int]] = []  # 已匹配区间，避免重叠

    for zh in sorted_keys:
        info = glossary.get(zh) or {}
        syns = info.get('synonyms', [])
        if not syns:
            continue
        start = 0
        while True:
            idx = text.find(zh, start)
            if idx < 0:
                break
            end = idx + len(zh)
            # 检查是否与已匹配区间重叠
            overlap = any(s < end and idx < e for s, e in consumed_spans)
            if not overlap:
                consumed_spans.append((idx, end))
                for syn in syns:
                    key = syn.lower()
                    if key not in seen and key not in text.lower():
                        seen.add(key)
                        extras.append(syn)
            start = end

    if extras:
        return f"{text} {' '.join(extras)}"
    return text
