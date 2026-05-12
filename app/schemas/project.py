from datetime import datetime
from pydantic import BaseModel


class ProjectCreate(BaseModel):
    title: str
    description: str = ""
    genre: str = ""


class ProjectUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    genre: str | None = None
    status: str | None = None


class ProjectResponse(BaseModel):
    id: str
    title: str
    description: str
    genre: str
    status: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
