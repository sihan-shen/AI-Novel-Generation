import uuid
from datetime import UTC, datetime

from sqlalchemy import Column, DateTime, String, Text

from app.database import Base


def _uuid():
    return str(uuid.uuid4())


class Project(Base):
    __tablename__ = "projects"

    id = Column(String, primary_key=True, default=_uuid)
    title = Column(String, nullable=False)
    description = Column(Text, default="")
    genre = Column(String, default="")
    status = Column(String, default="active")
    created_at = Column(DateTime, default=lambda: datetime.now(UTC))
    updated_at = Column(DateTime, default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC))  # noqa: E501
