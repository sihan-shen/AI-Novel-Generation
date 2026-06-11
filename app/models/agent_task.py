import uuid
from datetime import datetime

from sqlalchemy import Column, String, Integer, Text, DateTime, ForeignKey, Index

from app.database import Base


class AgentTask(Base):
    __tablename__ = "agent_tasks"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id = Column(String, ForeignKey("projects.id"), nullable=False)
    task_type = Column(String, nullable=False)
    target_desc = Column(Text, default="")
    autonomy_config = Column(Text, nullable=False, default="{}")
    orchestrator_state = Column(String, default="IDLE")
    blackboard_snapshot = Column(Text)
    status = Column(String, nullable=False, default="running")
    total_steps = Column(Integer, default=0)
    total_tokens = Column(Integer, default=0)
    last_committed_step = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)


Index("ix_agent_tasks_project_id", AgentTask.project_id)
Index("ix_agent_tasks_status", AgentTask.status)
Index("ix_agent_tasks_task_type", AgentTask.task_type)
