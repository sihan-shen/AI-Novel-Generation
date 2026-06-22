import uuid
from datetime import UTC, datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text

from app.database import Base


class Outline(Base):
    __tablename__ = "outlines"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id = Column(String, ForeignKey("projects.id"), nullable=False)
    parent_id = Column(String, ForeignKey("outlines.id"), nullable=True)
    level = Column(Integer, nullable=False)  # 1=volume, 2=chapter, 3=section
    sort_order = Column(Integer, nullable=False, default=0)
    title = Column(String, nullable=False)
    summary = Column(Text, default="")
    notes = Column(Text, default="")
    status = Column(String, default="draft")
    word_count_target = Column(Integer, default=0)
    word_count_actual = Column(Integer, default=0)
    pov_character = Column(String, default="")
    created_at = Column(DateTime, default=lambda: datetime.now(UTC))
    updated_at = Column(DateTime, default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC))  # noqa: E501
