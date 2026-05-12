import uuid
from datetime import datetime
from sqlalchemy import Column, String, Text, DateTime, ForeignKey, Float
from app.database import Base


class Style(Base):
    __tablename__ = "styles"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, nullable=False)
    source = Column(Text, default="")
    source_text = Column(Text, default="")
    analysis = Column(Text, default="{}")  # JSON
    tags = Column(Text, default="[]")  # JSON array
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class ProjectStyleLink(Base):
    __tablename__ = "project_style_links"

    project_id = Column(String, ForeignKey("projects.id", ondelete="CASCADE"), primary_key=True)
    style_id = Column(String, ForeignKey("styles.id", ondelete="CASCADE"), primary_key=True)
    weight = Column(Float, default=1.0)
