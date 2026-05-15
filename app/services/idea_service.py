from sqlalchemy.orm import Session
from app.models.idea import Idea


class IdeaService:
    @staticmethod
    def create(db: Session, project_id: str | None, title: str, content: str, source: str = "", tags: str = "[]") -> Idea:
        idea = Idea(project_id=project_id, title=title, content=content, source=source, tags=tags)
        db.add(idea)
        db.commit()
        db.refresh(idea)
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
        idea.status = "promoted"
        idea.promoted_to_type = target_type
        idea.promoted_to_id = target_id
        db.commit()
        return True

    @staticmethod
    def delete(db: Session, idea_id: str) -> bool:
        idea = db.query(Idea).filter(Idea.id == idea_id).first()
        if not idea:
            return False
        db.delete(idea)
        db.commit()
        return True
