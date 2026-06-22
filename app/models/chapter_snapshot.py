"""ChapterSnapshot — stores chapter content before agent modifications for rollback."""

import uuid
from datetime import UTC, datetime

from sqlalchemy import Column, DateTime, ForeignKey, Index, String, Text

from app.database import Base


class ChapterSnapshot(Base):
    __tablename__ = "chapter_snapshots"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    chapter_id = Column(String, ForeignKey("chapters.id", ondelete="CASCADE"), nullable=False)
    task_id = Column(String, ForeignKey("agent_tasks.id", ondelete="SET NULL"), nullable=True)
    content = Column(Text, default="")
    title = Column(String, default="")
    created_at = Column(DateTime, default=lambda: datetime.now(UTC))


Index("ix_chapter_snapshots_chapter_id", ChapterSnapshot.chapter_id)
Index("ix_chapter_snapshots_task_id", ChapterSnapshot.task_id)
