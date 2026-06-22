from datetime import UTC, datetime

from sqlalchemy import Column, DateTime, String, Text

from app.database import Base


class Config(Base):
    """Key-value store for app configuration (API keys, provider, etc.)."""
    __tablename__ = "app_config"

    key = Column(String, primary_key=True)
    value = Column(Text, default="")
    updated_at = Column(DateTime, default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC))  # noqa: E501
