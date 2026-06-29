from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ProjectCreate(BaseModel):
    name: str
    product: str = ''
    description: str = ''


class ProjectUpdate(BaseModel):
    name: str | None = None
    product: str | None = None
    description: str | None = None


class ProjectResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    product: str
    description: str
    created_at: datetime
    updated_at: datetime
