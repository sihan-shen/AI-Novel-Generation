import uuid
from datetime import UTC, datetime

from sqlalchemy import Column, DateTime, ForeignKey, Index, Integer, String, Text

from app.database import Base


class AgentMessage(Base):
    __tablename__ = "agent_messages"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    task_id = Column(String, ForeignKey("agent_tasks.id", ondelete="CASCADE"), nullable=False)
    role = Column(String, nullable=False)
    content = Column(Text, nullable=False)
    message_type = Column(String, nullable=False, default="text")
    msg_metadata = Column(Text)
    sequence = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime, default=lambda: datetime.now(UTC))


Index("ix_agent_messages_task_id", AgentMessage.task_id)
Index("ix_agent_messages_sequence", AgentMessage.sequence)
