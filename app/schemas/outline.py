from datetime import datetime

from pydantic import BaseModel, ConfigDict


class OutlineCreate(BaseModel):
    project_id: str
    parent_id: str | None = None
    level: int = 1
    sort_order: int = 0
    title: str
    summary: str = ""
    notes: str = ""


class OutlineUpdate(BaseModel):
    title: str | None = None
    summary: str | None = None
    notes: str | None = None
    status: str | None = None
    sort_order: int | None = None
    word_count_target: int | None = None
    pov_character: str | None = None


class OutlineResponse(BaseModel):
    id: str
    project_id: str
    parent_id: str | None
    level: int
    sort_order: int
    title: str
    summary: str
    notes: str
    status: str
    word_count_target: int
    word_count_actual: int
    pov_character: str
    created_at: datetime
    updated_at: datetime
    children: list["OutlineResponse"] = []

    model_config = ConfigDict(from_attributes=True)


OutlineResponse.model_rebuild()
