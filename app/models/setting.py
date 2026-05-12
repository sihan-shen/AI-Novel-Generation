import uuid
from datetime import datetime
from sqlalchemy import Column, String, Text, Integer, DateTime, ForeignKey
from app.database import Base


class Setting(Base):
    __tablename__ = "settings"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id = Column(String, ForeignKey("projects.id"), nullable=False)
    category = Column(String, nullable=False)
    name = Column(String, nullable=False)
    summary = Column(Text, default="")
    content = Column(Text, default="")
    structured_data = Column(Text, default="{}")  # JSON string
    weight = Column(Integer, default=5)
    sort_order = Column(Integer, default=0)
    key = Column(String, default="")
    status = Column(String, default="active")
    version = Column(Integer, default=1)
    tags = Column(Text, default="[]")  # JSON array
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class SettingRelation(Base):
    __tablename__ = "setting_relations"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    from_setting_id = Column(String, ForeignKey("settings.id", ondelete="CASCADE"), nullable=False)
    to_setting_id = Column(String, ForeignKey("settings.id", ondelete="CASCADE"), nullable=False)
    relation_type = Column(String, nullable=False)
    description = Column(Text, default="")
