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
    metadata_json = Column(Text, default="{}", name="metadata")
    updated_at = Column(DateTime, default=datetime.utcnow)

    @property
    def task_metadata(self) -> dict:
        import json
        try:
            return json.loads(self.metadata_json or "{}")
        except (json.JSONDecodeError, TypeError):
            return {}

    def set_task_metadata(self, data: dict):
        import json
        self.metadata_json = json.dumps(data, ensure_ascii=False)

    def update_task_metadata(self, **kwargs):
        md = self.task_metadata
        md.update(kwargs)
        self.set_task_metadata(md)


Index("ix_agent_tasks_project_id", AgentTask.project_id)
Index("ix_agent_tasks_status", AgentTask.status)
Index("ix_agent_tasks_task_type", AgentTask.task_type)
