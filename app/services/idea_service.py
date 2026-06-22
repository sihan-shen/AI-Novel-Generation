import logging

from sqlalchemy.orm import Session

from app.models.idea import Idea

logger = logging.getLogger(__name__)


class IdeaService:
    @staticmethod
    def create(db: Session, project_id: str | None, title: str, content: str, source: str = "", tags: str = "[]") -> Idea:  # noqa: E501
        idea = Idea(project_id=project_id, title=title, content=content, source=source, tags=tags)
        db.add(idea)
        db.commit()
        db.refresh(idea)
        logger.info("Created idea %s", idea.id)
        return idea

    @staticmethod
    def list_by_project(db: Session, project_id: str | None = None) -> list[Idea]:
        q = db.query(Idea).filter(Idea.status == "active")
        if project_id:
            q = q.filter((Idea.project_id == project_id) | (Idea.project_id.is_(None)))
        return q.order_by(Idea.sort_order, Idea.created_at.desc()).all()

    @staticmethod
    def reorder(db: Session, items: list[dict]) -> None:
        for item in items:
            db.query(Idea).filter(Idea.id == item["id"]).update(
                {"sort_order": item["sort_order"]}
            )
        db.commit()

    @staticmethod
    def promote(db: Session, idea_id: str, target_type: str, target_id: str) -> bool:
        idea = db.query(Idea).filter(Idea.id == idea_id).first()
        if not idea:
            return False
        idea.status = "promoted"  # type: ignore[assignment]
        idea.promoted_to_type = target_type  # type: ignore[assignment]
        idea.promoted_to_id = target_id  # type: ignore[assignment]
        db.commit()
        return True

    @staticmethod
    def delete(db: Session, idea_id: str) -> bool:
        idea = db.query(Idea).filter(Idea.id == idea_id).first()
        if not idea:
            logger.warning("Delete failed: idea %s not found", idea_id)
            return False
        db.delete(idea)
        db.commit()
        logger.info("Deleted idea %s", idea_id)
        return True
