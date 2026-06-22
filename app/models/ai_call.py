import uuid
from datetime import UTC, datetime

from sqlalchemy import Column, DateTime, ForeignKey, Index, Integer, String, Text

from app.database import Base


class AICall(Base):
    __tablename__ = "ai_call"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id = Column(String, ForeignKey("projects.id"), nullable=True)
    scenario = Column(String, nullable=False)
    model = Column(String, nullable=False)
    prompt = Column(Text, default="")
    response = Column(Text, default="")
    input_tokens = Column(Integer, default=0)
    output_tokens = Column(Integer, default=0)
    duration_ms = Column(Integer, nullable=True)
    status = Column(String, default="success")
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(UTC))


Index("ai_call_created_idx", AICall.created_at.desc())
Index("ai_call_scenario_idx", AICall.scenario)
Index("ai_call_project_idx", AICall.project_id)
