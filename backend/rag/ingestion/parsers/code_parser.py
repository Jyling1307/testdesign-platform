"""代码图谱 JSON 适配器（从 langchain 迁移）。

📌 玲玲大人已有结构化代码图谱 JSON。格式：

{
  "modules": [
    {
      "module_name": "用户认证模块",
      "file_path": "src/auth/login.py",
      "functions": [
        {"name": "login", "params": [...], "operations": ["校验密码", "生成token"]}
      ],
      "dependencies": ["src/db/user.py"]
    }
  ]
}

每个 operation 产出一个 spec 级节点，挂在所属模块下。
"""
import json

from rag.common.chunk import ChunkNode
from rag.config import RAGConfig


def parse_code_graph(path: str, doc_id: str) -> list[ChunkNode]:
    """解析代码图谱 JSON，返回 ChunkNode 列表。"""
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    nodes: list[ChunkNode] = []
    seq = 0

    for module in data.get("modules", []):
        module_name = module.get("module_name") or module.get("name") or "未命名模块"
        file_path = module.get("file_path", "")
        module_path = module_name

        deps = module.get("dependencies", [])
        module_content = f"## 模块：{module_name}\n路径：{file_path}"
        if deps:
            module_content += "\n依赖：" + ", ".join(deps)
        module_node = ChunkNode(
            content=module_content,
            level=RAGConfig.LEVEL_FEATURE,
            module_path=module_path,
            doc_id=doc_id,
            source_type="code",
            id=f"{doc_id}-m{seq}",
        )
        nodes.append(module_node)
        module_parent_id = module_node.id
        seq += 1

        for func in module.get("functions", []):
            func_name = func.get("name", "")
            params = func.get("params", [])
            operations = func.get("operations", [])
            for op in operations:
                content = f"[{module_name} > {func_name}] 操作点：{op}"
                if params:
                    content += f"（参数：{', '.join(map(str, params))}）"
                nodes.append(ChunkNode(
                    content=content,
                    level=RAGConfig.LEVEL_SPEC,
                    parent_id=module_parent_id,
                    module_path=f"{module_path}/{func_name}",
                    doc_id=doc_id,
                    source_type="code",
                    id=f"{doc_id}-c{seq}",
                ))
                seq += 1

    return nodes
