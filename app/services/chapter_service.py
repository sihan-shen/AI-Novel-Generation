from sqlalchemy.orm import Session
from app.models.chapter import Chapter
from app.schemas.chapter import ChapterCreate, ChapterUpdate


class ChapterService:
    @staticmethod
    def create(db: Session, data: ChapterCreate) -> Chapter:
        ch = Chapter(**data.model_dump())
        ch.word_count = len(ch.content) if ch.content else 0
        db.add(ch)
        db.commit()
        db.refresh(ch)
        return ch

    @staticmethod
    def get(db: Session, chapter_id: str) -> Chapter | None:
        return db.query(Chapter).filter(Chapter.id == chapter_id).first()

    @staticmethod
    def list_by_project(db: Session, project_id: str) -> list[Chapter]:
        return db.query(Chapter).filter(Chapter.project_id == project_id).order_by(Chapter.sort_order).all()

    @staticmethod
    def update(db: Session, chapter_id: str, data: ChapterUpdate) -> Chapter | None:
        ch = ChapterService.get(db, chapter_id)
        if not ch:
            return None
        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(ch, field, value)
        ch.word_count = len(ch.content) if ch.content else 0
        db.commit()
        db.refresh(ch)
        return ch

    @staticmethod
    def delete(db: Session, chapter_id: str) -> bool:
        ch = ChapterService.get(db, chapter_id)
        if not ch:
            return False
        db.delete(ch)
        db.commit()
        return True
