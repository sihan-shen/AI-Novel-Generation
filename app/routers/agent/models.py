"""Pydantic request models for agent endpoints."""

from pydantic import BaseModel


class ChatRequest(BaseModel):
    message: str
    chapter_outline_id: str | None = None
    target_words: int = 3000


class ConfirmRequest(BaseModel):
    confirm_id: str
    action: str  # 'approve' | 'reject' | 'modify'
    modification: str | None = None


class CancelRequest(BaseModel):
    confirm_id: str | None = None
    task_id: str | None = None


class ConfirmInspirationsRequest(BaseModel):
    inspiration_ids: list[str]
