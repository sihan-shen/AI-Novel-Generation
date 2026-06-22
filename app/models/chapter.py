import uuid
from datetime import UTC, datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text

from app.database import Base


class Chapter(Base):
    __tablename__ = "chapters"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id = Column(String, ForeignKey("projects.id"), nullable=False)
    outline_id = Column(String, ForeignKey("outlines.id"), nullable=True)
    title = Column(String, nullable=False)
    content = Column(Text, default="")
    sort_order = Column(Integer, nullable=False, default=0)
    status = Column(String, default="draft")
    word_count = Column(Integer, default=0)
    notes = Column(Text, default="")
    generated_by_type = Column(String, nullable=True)
    generated_by_task_id = Column(String, ForeignKey("agent_tasks.id"), nullable=True)
    generation_prompt = Column(Text, default="")
    created_at = Column(DateTime, default=lambda: datetime.now(UTC))
    updated_at = Column(DateTime, default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC))  # noqa: E501


class ChapterSettingLink(Base):
    __tablename__ = "chapter_setting_links"

    chapter_id = Column(String, ForeignKey("chapters.id", ondelete="CASCADE"), primary_key=True)
    setting_id = Column(String, ForeignKey("settings.id", ondelete="CASCADE"), primary_key=True)
