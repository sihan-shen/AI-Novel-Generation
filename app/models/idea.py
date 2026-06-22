import uuid
from datetime import UTC, datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text

from app.database import Base


class Idea(Base):
    __tablename__ = "ideas"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id = Column(String, ForeignKey("projects.id"), nullable=True)
    title = Column(String, default="")
    content = Column(Text, default="")
    source = Column(String, default="")
    tags = Column(Text, default="[]")
    status = Column(String, default="active")
    promoted_to_type = Column(String, nullable=True)
    promoted_to_id = Column(String, nullable=True)
    sort_order = Column(Integer, default=0)
    created_at = Column(DateTime, default=lambda: datetime.now(UTC))
    updated_at = Column(DateTime, default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC))  # noqa: E501
