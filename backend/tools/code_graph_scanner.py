"""扫描 Python 仓库生成代码图谱 JSON（供 RAG code_parser 入库）。

输出格式匹配 rag/ingestion/parsers/code_parser.py：
{
  "modules": [{
    "module_name": "api.base_api.ide_base_request",
    "file_path": "api/base_api/ide_base_request.py",
    "functions": [{"name": "ide_login", "params": [...], "operations": ["调用 send", "断言 ..."]}],
    "dependencies": ["requests", "boto", "api.base_api.idm_base_request"]
  }]
}

用法：
    python tools/code_graph_scanner.py                # 扫描全部 4 个仓库
    python tools/code_graph_scanner.py v3             # 只扫 v3
    python tools/code_graph_scanner.py v3 om           # 扫 v3 + om
"""
import ast
import os
import json
import sys
from pathlib import Path

EXCLUDE_DIRS = {
    'venv', '__pycache__', '.git', 'node_modules', '.tox',
    'dist', 'build', '.eggs', 'site-packages', '.venv', 'env',
    'migrations', '.code-review-graph',
}
EXCLUDE_FILES = {'__init__.py', 'setup.py', 'conftest.py'}
# 过滤琐碎函数调用（不算"操作点"）
TRIVIAL_CALLS = {
    'append', 'pop', 'get', 'set', 'items', 'keys', 'values', 'format',
    'print', 'len', 'range', 'enumerate', 'zip', 'sorted', 'reversed',
    'isinstance', 'hasattr', 'getattr', 'setattr', 'dict', 'list', 'tuple',
    'set', 'frozenset', 'str', 'int', 'float', 'bool', 'type', 'open',
    'split', 'join', 'strip', 'replace', 'lower', 'upper', 'encode', 'decode',
}

REPOS = {
    'v3': 'D:/桌面/工作文档/自动化代码/v3/sandstone_idmtestkit',
    'v5': 'D:/桌面/工作文档/自动化代码/v5/sandstone_idmtestkit',
    'mos_v6': 'D:/桌面/工作文档/存储自动化看护/MOS V6/sandstone_autotestkit',
    'om': 'D:/桌面/工作文档/自动化代码/om/sandstone_management_platform',
}
OUTPUT_DIR = 'D:/桌面/工作文档/testdesign-platform/backend/data/knowledge'


def extract_operations(func_node) -> list[str]:
    """从函数 AST 节点提取关键操作点（函数调用 + assert）。"""
    ops = []
    for node in ast.walk(func_node):
        if isinstance(node, ast.Call):
            try:
                full = ast.unparse(node.func)
            except Exception:
                continue
            short = full.split('.')[-1].strip('()')
            # 过滤琐碎调用和 self.xxx 赋值型
            if short in TRIVIAL_CALLS or short.startswith('_'):
                continue
            ops.append(f"调用 {full}")
        elif isinstance(node, ast.Assert):
            try:
                cond = ast.unparse(node.test)[:60]
                ops.append(f"断言 {cond}")
            except Exception:
                ops.append("断言验证")
    # 去重保序
    seen = set()
    result = []
    for op in ops:
        if op not in seen:
            seen.add(op)
            result.append(op)
    return result[:15]  # 每函数最多 15 个操作点


def extract_functions(tree) -> list[dict]:
    """提取文件内所有顶层函数 + 类方法（含所属类名）。"""
    funcs = []

    def _walk(node, class_name=None):
        for child in ast.iter_child_nodes(node):
            if isinstance(child, ast.ClassDef):
                _walk(child, class_name=child.name)
            elif isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                name = child.name
                if name.startswith('_'):
                    continue
                if class_name:
                    name = f"{class_name}.{name}"
                params = [a.arg for a in child.args.args if not a.arg.startswith('_')][:6]
                operations = extract_operations(child)
                if not operations:
                    continue  # 没有操作点的函数跳过（减少噪音）
                funcs.append({
                    'name': name,
                    'params': params,
                    'operations': operations,
                })
                # 不递归进函数体（避免重复）

    _walk(tree)
    return funcs


def extract_dependencies(tree) -> list[str]:
    """提取 import 依赖（顶层模块名，去重）。"""
    deps = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                deps.add(alias.name.split('.')[0])
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                deps.add(node.module.split('.')[0])
    return sorted(d for d in deps if d and not d.startswith('_'))


def scan_file(file_path: Path, repo_root: Path) -> dict | None:
    """扫描单个 Python 文件，返回 module dict（无函数则返回 None）。"""
    try:
        source = file_path.read_text(encoding='utf-8', errors='ignore')
        tree = ast.parse(source, filename=str(file_path))
    except (SyntaxError, ValueError, OSError):
        return None
    except Exception:
        return None

    rel = file_path.relative_to(repo_root)
    module_name = str(rel.with_suffix('')).replace('\\', '/').replace('/', '.')

    functions = extract_functions(tree)
    if not functions:
        return None

    return {
        'module_name': module_name,
        'file_path': str(rel).replace('\\', '/'),
        'functions': functions,
        'dependencies': extract_dependencies(tree),
    }


def scan_repo(repo_path: str, output_path: str, repo_name: str = '') -> int:
    """扫描整个仓库，输出 JSON。返回模块数。"""
    repo = Path(repo_path)
    if not repo.exists():
        print(f"⚠️  路径不存在: {repo_path}")
        return 0

    modules = []
    scanned = 0
    for root, dirs, files in os.walk(repo):
        dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS and not d.startswith('.')]
        for fname in files:
            if not fname.endswith('.py') or fname in EXCLUDE_FILES:
                continue
            fp = Path(root) / fname
            scanned += 1
            mod = scan_file(fp, repo)
            if mod:
                modules.append(mod)

    output = {'modules': modules}
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    total_funcs = sum(len(m['functions']) for m in modules)
    total_ops = sum(len(fn['operations']) for m in modules for fn in m['functions'])
    size_kb = Path(output_path).stat().st_size // 1024
    print(f"✅ {repo_name or repo.name}: 扫描 {scanned} 文件 → {len(modules)} 模块, "
          f"{total_funcs} 函数, {total_ops} 操作点 ({size_kb}KB)")
    print(f"   输出: {output_path}")
    return len(modules)


def main():
    # 命令行参数：指定要扫描的仓库名（空=全部）
    targets = sys.argv[1:] if len(sys.argv) > 1 else list(REPOS.keys())
    unknown = [t for t in targets if t not in REPOS]
    if unknown:
        print(f"❌ 未知仓库名: {unknown}")
        print(f"   可选: {list(REPOS.keys())}")
        return 1

    print(f"=== 扫描目标: {targets} ===\n")
    total = 0
    for name in targets:
        path = REPOS[name]
        output = f"{OUTPUT_DIR}/code_graph_{name}.json"
        print(f"[{name}] {path}")
        total += scan_repo(path, output, repo_name=name)
        print()

    print(f"=== 全部完成: 共 {total} 模块 ===")
    print(f"\n💡 入库命令（关闭 tagger 加速，代码图谱本身有清晰命名）:")
    print(f"   cd backend && python -c 'from rag.config import RAGConfig; RAGConfig.TAGGER_ENABLED=False; from rag.ingestion.ingest_service import ingest_file; print(ingest_file(\"data/knowledge/code_graph_v3.json\", doc_id=\"code_v3\"))'")
    return 0


if __name__ == '__main__':
    sys.exit(main())
