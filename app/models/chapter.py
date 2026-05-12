import uuid
from datetime import datetime
from sqlalchemy import Column, String, Text, Integer, DateTime, ForeignKey
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
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class ChapterSettingLink(Base):
    __tablename__ = "chapter_setting_links"

    chapter_id = Column(String, ForeignKey("chapters.id", ondelete="CASCADE"), primary_key=True)
    setting_id = Column(String, ForeignKey("settings.id", ondelete="CASCADE"), primary_key=True)
