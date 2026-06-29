"""统一的文档节点数据结构（从 langchain 迁移）。

贯穿「解析 → 切分 → 入库 → 检索」全流程，保证各模块用同一种结构传递。
用 Pydantic 便于校验和序列化。
"""
import uuid

from pydantic import BaseModel, Field


class ChunkNode(BaseModel):
    """一个文档块（可能是一个功能模块/功能点/规格边界/表格）。"""

    content: str  # 文本内容（表格存 markdown 字符串）
    level: str = "spec"  # module / feature / spec
    parent_id: str | None = None  # 父节点 id（small-to-big 回溯上下文用）
    source_type: str = "design_doc"  # design_doc / test_design / code
    doc_id: str = ""  # 所属文档 id
    module_path: str = ""  # 层级路径，如 "登录模块/密码找回"
    terms: list[str] = Field(default_factory=list)  # 命中的术语（用于过滤召回）
    node_type: str = "text"  # text / table / image
    extra: dict = Field(default_factory=dict)
    id: str = Field(default_factory=lambda: uuid.uuid4().hex)

    def to_metadata(self) -> dict:
        """转 Chroma metadata（Chroma 的 metadata 值只支持 str/int/float/bool）。"""
        return {
            "id": self.id,
            "level": self.level,
            "parent_id": self.parent_id or "",
            "source_type": self.source_type,
            "doc_id": self.doc_id,
            "module_path": self.module_path,
            "node_type": self.node_type,
            "terms": ",".join(self.terms),
            # 标签：拆成独立字段便于 Chroma where 过滤
            "tag_module": (self.extra.get("tags") or {}).get("module", ""),
            "tag_test_type": (self.extra.get("tags") or {}).get("test_type", ""),
            "tag_priority": (self.extra.get("tags") or {}).get("priority", ""),
        }
