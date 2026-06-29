from pydantic import BaseModel, ConfigDict


class TestCaseResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    test_design_id: int
    name: str
    product: str
    case_type: str
    phase: str
    precondition: str
    steps: str
    expected_result: str
    source_node_path: str


class TestCaseCreate(BaseModel):
    test_design_id: int
    name: str
    product: str = ''
    case_type: str = '功能测试'
    phase: str = ''
    precondition: str = ''
    steps: str = ''
    expected_result: str = ''
    source_node_path: str = ''
