from datetime import datetime

from pydantic import BaseModel, ConfigDict


class DocumentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    title: str
    file_path: str
    file_size: int
    file_type: str
    raw_text: str
    parsed_structure: dict
    status: str
    created_at: datetime


class DocumentCreate(BaseModel):
    project_id: int
    title: str
