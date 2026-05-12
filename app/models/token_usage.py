import uuid
from datetime import datetime
from sqlalchemy import Column, String, Integer, DateTime
from app.database import Base


class TokenUsage(Base):
    __tablename__ = "token_usage"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    model = Column(String, nullable=False)
    input_tokens = Column(Integer, default=0)
    output_tokens = Column(Integer, default=0)
    scenario = Column(String, default="")
    created_at = Column(DateTime, default=datetime.utcnow)
