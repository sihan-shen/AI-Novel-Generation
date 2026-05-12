import uuid
from datetime import datetime
from sqlalchemy import Column, String, Text, DateTime, ForeignKey
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
    created_at = Column(DateTime, default=datetime.utcnow)
