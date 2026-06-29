"""Parse step2 section of test design MD into structured test cases.

Uses level-based parsing for the 5-level hierarchy:
- L1: 测试类型 (case_type)
- L2: 用例标题 (name)
- L3: 前置条件 or 操作步骤
- L4: 预期结果
- L5: 待确认 (需与开发确认)
"""

import re

# Test type mapping from MD to xlsx column value
TYPE_MAP = {
    '功能测试': '功能测试',
    '功能交互': '功能交互',
    '场景测试': '场景测试',
    '兼容性': '兼容性',
    '自动化测试': '自动化测试',
    '易用性测试': '易用性测试',
    '性能测试': '性能基线测试',
    '性能基线测试': '性能基线测试',
    '性能极限测试': '性能极限测试',
    '业务影响性能测试': '业务影响性能测试',
    '可靠性测试': '可靠性测试',
    '升级测试': '升级测试',
    '压力测试': '压力测试',
    '长稳': '长稳测试',
    '长稳测试': '长稳测试',
}

# Keywords that suggest a line is a precondition (environment setup) rather than an action
PRECONDITION_MARKERS = [
    '准备：', '前提：', '已配置', '已创建', '已开启', '环境中',
    '已存在', '已上传', '已部署', '预埋', '工作目录下有',
]


def extract_step2(full_md: str) -> str:
    """Extract the step2 section from full MD text, skipping the step2 header line."""
    lines = full_md.split('\n')
    start_idx = None
    end_idx = len(lines)

    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith('- step2'):
            start_idx = i
            continue
        if start_idx is not None and stripped.startswith('- step3'):
            end_idx = i
            break

    if start_idx is None:
        return ''

    # Skip the "- step2" header line and its immediately following description lines
    # Start from the first bullet line after the header
    content_start = start_idx + 1
    for j in range(start_idx + 1, end_idx):
        if lines[j].strip().startswith('- '):
            content_start = j
            break

    return '\n'.join(lines[content_start:end_idx])


def _is_precondition(text: str) -> bool:
    """Check if a node text describes a precondition (environment state) vs an action."""
    for marker in PRECONDITION_MARKERS:
        if marker in text:
            return True
    return False


def parse_step2_to_cases(step2_text: str, product: str = '') -> list[dict]:
    """Parse step2 markdown into structured test case dicts.

    Uses the 5-level hierarchy:
    - L1 under type branch: test type (mapped via TYPE_MAP)
    - L2: test case title
    - L3: precondition or operation step
    - L4: expected result
    - L5: 待确认 note

    Returns list of dicts with keys: name, product, case_type, phase, precondition, steps, expected
    """
    if not step2_text:
        return []

    # Parse bullet tree
    lines = step2_text.split('\n')
    nodes = []
    for line in lines:
        stripped = line.strip()
        if not stripped.startswith('- '):
            continue
        indent = len(line) - len(line.lstrip())
        level = indent // 4 + 1
        text = stripped[2:]  # Remove '- '
        nodes.append({'level': level, 'text': text, 'children': []})

    if not nodes:
        return []

    # Build tree structure
    root = {'level': 0, 'text': 'root', 'children': []}
    stack = [root]
    for node in nodes:
        while len(stack) > 1 and stack[-1]['level'] >= node['level']:
            stack.pop()
        stack[-1]['children'].append(node)
        stack.append(node)

    # Detect if first child is '测试类型分析' wrapper
    type_nodes = []
    if root['children']:
        first_child = root['children'][0]
        if '测试类型' in first_child['text'].strip():
            # Unwrap: use grandchildren of the wrapper as type branches
            type_nodes = first_child['children']
        else:
            # Direct type nodes
            type_nodes = root['children']

    # Process each test type branch
    cases = []
    for type_node in type_nodes:
        type_name = type_node['text'].strip()
        xlsx_type = TYPE_MAP.get(type_name, type_name)
        if '跨协议' in type_name or '兼容性' in type_name:
            xlsx_type = '功能测试'

        for case_node in type_node['children']:
            _process_case_node(case_node, product, xlsx_type, cases)

    return cases


def _process_case_node(node, product: str, case_type: str, cases: list):
    """Process a single case tree (L2 and below) into a test case dict.

    Expected structure under a type branch:
      L2: 用例标题
        L3: 前置条件 or 操作步骤
          L4: 预期结果
            L5: 待确认 (optional)
    """
    case_name = node['text'].strip()
    path_parts = [case_name]

    preconditions = []
    step_list = []
    expected_list = []

    def collect(children, depth=0):
        for child in children:
            child_text = child['text'].strip()
            child_level = child['level']
            has_children = bool(child['children'])

            # Determine role by relative depth and content
            if child_level == node['level'] + 1:
                # L3 under case title: could be precondition or step
                if _is_precondition(child_text):
                    preconditions.append(child_text)
                else:
                    # This is a step - collect its L4 children as expected results
                    step = child_text
                    exp_parts = []
                    for gc in child['children']:
                        gc_text = gc['text'].strip()
                        # L5 (待确认) stays as expected with note
                        for ggc in gc['children']:
                            gc_text += f'（{ggc["text"].strip()}）'
                        if gc_text:
                            exp_parts.append(gc_text)
                    step_list.append((step, exp_parts))
            elif child_level == node['level'] + 2 and not has_children:
                # L4 without L3 parent (unusual but handle gracefully)
                expected_list.append(child_text)

    collect(node['children'])

    # Build case dict
    case = {
        'name': case_name,
        'product': product,
        'case_type': case_type,
        'phase': '',
        'precondition': '\n'.join(preconditions) if preconditions else '',
        'steps': '\n'.join(f'{i + 1}、{s}' for i, (s, _) in enumerate(step_list)) if step_list else '',
        'expected': '\n'.join(
            exp for _, exps in step_list for exp in exps
        ) if step_list else '\n'.join(expected_list),
    }
    cases.append(case)

    # Handle deeper nesting: L2 may have sub-categories that contain L3+ cases
    for child in node['children']:
        if child['children'] and any(gc['children'] for gc in child['children']):
            # This child has deeper structure - it's a sub-case
            _process_case_node(child, product, case_type, cases)
