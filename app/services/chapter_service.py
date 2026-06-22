import logging

from sqlalchemy.orm import Session

from app.models.chapter import Chapter
from app.schemas.chapter import ChapterCreate, ChapterUpdate

logger = logging.getLogger(__name__)


class ChapterService:
    @staticmethod
    def create(db: Session, data: ChapterCreate) -> Chapter:
        ch = Chapter(**data.model_dump())
        ch.word_count = len(ch.content) if ch.content else 0  # type: ignore[assignment]
        db.add(ch)
        db.commit()
        db.refresh(ch)
        logger.info("Created chapter %s (project %s)", ch.id, ch.project_id)
        return ch

    @staticmethod
    def get(db: Session, chapter_id: str) -> Chapter | None:
        return db.query(Chapter).filter(Chapter.id == chapter_id).first()

    @staticmethod
    def list_by_project(db: Session, project_id: str) -> list[Chapter]:
        return db.query(Chapter).filter(Chapter.project_id == project_id).order_by(Chapter.sort_order).all()  # noqa: E501

    @staticmethod
    def update(db: Session, chapter_id: str, data: ChapterUpdate) -> Chapter | None:
        ch = ChapterService.get(db, chapter_id)
        if not ch:
            return None
        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(ch, field, value)
        ch.word_count = len(ch.content) if ch.content else 0  # type: ignore[assignment]
        db.commit()
        db.refresh(ch)
        return ch

    @staticmethod
    def reorder(db: Session, items: list[dict]) -> None:
        for item in items:
            db.query(Chapter).filter(Chapter.id == item["id"]).update(
                {"sort_order": item["sort_order"]}
            )
        db.commit()

    @staticmethod
    def delete(db: Session, chapter_id: str) -> bool:
        ch = ChapterService.get(db, chapter_id)
        if not ch:
            logger.warning("Delete failed: chapter %s not found", chapter_id)
            return False
        db.delete(ch)
        db.commit()
        logger.info("Deleted chapter %s", chapter_id)
        return True
