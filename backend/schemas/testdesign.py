from datetime import datetime

from pydantic import BaseModel, ConfigDict


class TestDesignResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    document_id: int
    version: int
    full_md: str
    xlsx_file_path: str | None
    status: str
    created_at: datetime
    updated_at: datetime
    reviews: list = []


class TestDesignCreate(BaseModel):
    project_id: int
    document_id: int


class ReviewItem(BaseModel):
    node_path: str
    node_text: str = ''
    status: str = 'pending'
    feedback: str = ''


class RefineRequest(BaseModel):
    feedback: str
    rejected_nodes: list[dict] = []
    test_types: list[str] | None = None


class SyncKBRequest(BaseModel):
    mode: str = 'A'


class PreviewXlsxRequest(BaseModel):
    file: bytes | None = None
