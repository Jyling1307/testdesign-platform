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
