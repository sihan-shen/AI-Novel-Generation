from pydantic import BaseModel


class SettingCreate(BaseModel):
    project_id: str
    category: str
    name: str
    summary: str = ""
    content: str = ""
    structured_data: str = "{}"
    weight: int = 5
    key: str = ""
    tags: str = "[]"


class SettingUpdate(BaseModel):
    name: str | None = None
    category: str | None = None
    summary: str | None = None
    content: str | None = None
    structured_data: str | None = None
    weight: int | None = None
    status: str | None = None
    tags: str | None = None


class SettingRelationCreate(BaseModel):
    from_setting_id: str
    to_setting_id: str
    relation_type: str
    description: str = ""
