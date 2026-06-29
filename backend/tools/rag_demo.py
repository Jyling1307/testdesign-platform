"""RAG 流程演示脚本：输入开发设计文字，看完整 4 步 pipeline 全过程。

用法：
    python tools/rag_demo.py                 # 用内置示例文字演示
    python tools/rag_demo.py doc.txt         # 从文件读
    python tools/rag_demo.py -i              # 交互输入（粘贴后 Ctrl+Z+Enter 结束）
"""
import sys
import time
import asyncio
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# 内置演示文字（不传参数时用这个）
DEMO_TEXT = """# 快照创建功能

支持对指定卷创建时间点快照，可用于数据回滚。创建时支持指定快照名称，名称在同一卷内不可重复。"""


def hr(c='═', n=72):
    print(c * n)


def get_input_text():
    """获取输入文本：文件参数 > 交互输入 > 内置示例。"""
    if len(sys.argv) > 1 and sys.argv[1] != '-i':
        path = Path(sys.argv[1])
        if not path.exists():
            print(f'文件不存在: {path}')
            sys.exit(1)
        return path.read_text(encoding='utf-8'), f'文件 {path.name}'
    elif len(sys.argv) > 1 and sys.argv[1] == '-i':
        print('请粘贴开发设计文字（结束后按 Enter，再按 Ctrl+Z，再按 Enter）：')
        print('-' * 50)
        content = sys.stdin.read()
        return content.strip(), '交互输入'
    else:
        return DEMO_TEXT, '内置示例（CIFS 共享审计日志功能）'


async def run_pipeline_and_show(document_text, source):
    print()
    hr()
    print(f'  输入来源: {source} | {len(document_text)} 字符')
    hr()
    print(document_text[:400] + ('...' if len(document_text) > 400 else ''))

    # ============ 步骤 1 ============
    print()
    hr('◆')
    print('  步骤 1/4: 提取测试点  (extract_test_points)')
    hr('◆')
    from rag.pipeline.orchestrator import extract_test_points
    t = time.time()
    test_points = extract_test_points(document_text)
    print(f'  耗时: {time.time()-t:.1f}s | LLM 调用: 1 次 | 提取测试点: {len(test_points)} 个')
    print('-' * 72)
    for i, tp in enumerate(test_points, 1):
        print(f'  {i:2d}. {tp}')

    # ============ 步骤 2 ============
    print()
    hr('◆')
    print('  步骤 2/4: 批量扩写检索问题  (batch_expand_queries)  ★ 核心优化')
    hr('◆')
    from rag.retrieval.query_expander import batch_expand_queries
    t = time.time()
    queries = batch_expand_queries(test_points)
    print(f'  耗时: {time.time()-t:.1f}s | LLM 调用: 1 次 | 扩写检索问题: {len(queries)} 个')
    print(f'  优化对比: 原方案 {len(test_points)} 测试点 = {len(test_points)} 次串行 LLM | 现方案 1 次批量')
    print('-' * 72)
    for i, q in enumerate(queries[:20], 1):
        print(f'  {i:2d}. {q}')
    if len(queries) > 20:
        print(f'  ... 共 {len(queries)} 个')

    # ============ 步骤 3 ============
    print()
    hr('◆')
    print('  步骤 3/4: 多源检索 + few-shot 学风格  (retrieve_context)')
    hr('◆')
    from rag.pipeline.orchestrator import retrieve_context
    t = time.time()
    retrieved = retrieve_context(queries)
    elapsed = time.time() - t
    print(f'  耗时: {elapsed:.1f}s | LLM 调用: 1 次(query打标签) | 检索: 向量+rerank+父子回溯')
    print(f'  检索上下文: {len(retrieved["raw"])} 条 | few-shot 学风格示例: {len(retrieved["few_shot"])} 字符')
    print('-' * 72)
    print('  检索到的知识库内容（喂给生成步骤的上下文）:')
    for i, (doc, score, meta) in enumerate(retrieved['raw'][:5], 1):
        src = meta.get('source_type', '')
        mp = meta.get('module_path', '') or meta.get('doc_id', '')
        tag_m = meta.get('tag_module', '')
        tag_t = meta.get('tag_test_type', '')
        tag_info = f' | 标签:{tag_m}/{tag_t}' if (tag_m or tag_t) else ''
        print(f'  [{i}] 来源:{src} | {mp}{tag_info} | rerank分:{score:.3f}')
        print(f'       {doc[:120]}{"..." if len(doc) > 120 else ""}')

    # ============ 步骤 4 ============
    print()
    hr('◆')
    print('  步骤 4/4: 流式生成测试设计  (stream_generate_design_md)')
    hr('◆')
    from rag.pipeline.orchestrator import stream_generate_design_md
    print('  LLM 流式生成中（实时显示）...')
    print('=' * 72)
    t = time.time()
    full_md = ''
    async for chunk in stream_generate_design_md(
        test_points=test_points,
        context=retrieved['context'],
        few_shot=retrieved['few_shot'],
        document_text=document_text,
    ):
        print(chunk, end='', flush=True)
        full_md += chunk
    print()
    print('=' * 72)
    print(f'  耗时: {time.time()-t:.1f}s | LLM 调用: 1 次(流式) | 生成: {len(full_md)} 字符')

    # ============ 总结 ============
    print()
    hr()
    print('  全流程总结')
    hr()
    print(f'  步骤1 提取测试点:   {len(test_points):4d} 个')
    print(f'  步骤2 扩写问题:     {len(queries):4d} 个')
    print(f'  步骤3 检索上下文:   {len(retrieved["raw"]):4d} 条 + few-shot {len(retrieved["few_shot"])} 字符')
    print(f'  步骤4 生成设计:     {len(full_md):4d} 字符')
    print(f'  总 LLM 调用:        4 次 (extract + expand + tag_query + generate)')


def main():
    text, source = get_input_text()
    if not text:
        print('输入为空，退出')
        return
    print(f'\nRAG 4 步 pipeline 演示（知识库 199063 节点）')
    asyncio.run(run_pipeline_and_show(text, source))


if __name__ == '__main__':
    main()
