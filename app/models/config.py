from datetime import datetime
from sqlalchemy import Column, String, Text, DateTime
from app.database import Base


class Config(Base):
    """Key-value store for app configuration (API keys, provider, etc.)."""
    __tablename__ = "app_config"

    key = Column(String, primary_key=True)
    value = Column(Text, default="")
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
