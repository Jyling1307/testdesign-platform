"""Parse xlsx test case file into structured case dicts."""

import openpyxl
from io import BytesIO

HEADERS = ['用例名称', '所属产品', '用例类型', '适用阶段', '前置条件', '步骤', '预期结果']


def parse_xlsx_to_cases(xlsx_bytes):
    """Parse xlsx bytes into list of case dicts.

    Dict keys match md_parser.parse_step2_to_cases output format:
    name, product, case_type, phase, precondition, steps, expected
    """
    wb = openpyxl.load_workbook(BytesIO(xlsx_bytes), read_only=True)
    ws = wb.active
    rows = list(ws.iter_rows(values_only=True))
    wb.close()

    if not rows:
        return []

    cases = []
    for row in rows[1:]:  # skip header
        if not row or not any(row):
            continue
        case = {
            'name': str(row[0] or '').strip(),
            'product': str(row[1] or '').strip(),
            'case_type': str(row[2] or '功能测试').strip(),
            'phase': str(row[3] or '').strip(),
            'precondition': str(row[4] or '').strip(),
            'steps': str(row[5] or '').strip(),
            'expected': str(row[6] or '').strip(),
        }
        if case['name']:
            cases.append(case)
    return cases
