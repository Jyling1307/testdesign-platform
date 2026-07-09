from datetime import datetime
from typing import Any

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
    parsed_structure: Any  # list[{text, style, level}]，各 parser 均返回 list
    status: str
    created_at: datetime


class DocumentCreate(BaseModel):
    project_id: int
    title: str
