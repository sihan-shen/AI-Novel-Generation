import logging

from sqlalchemy.orm import Session

from app.models.outline import Outline
from app.schemas.outline import OutlineCreate, OutlineUpdate

logger = logging.getLogger(__name__)


class OutlineService:
    @staticmethod
    def create(db: Session, data: OutlineCreate) -> Outline:
        max_order = db.query(Outline.sort_order).filter(
            Outline.project_id == data.project_id,
            Outline.parent_id == data.parent_id,
            Outline.level == data.level,
        ).order_by(Outline.sort_order.desc()).first()
        sort_order = (max_order[0] + 1) if max_order else 1
        obj = Outline(
            project_id=data.project_id,
            parent_id=data.parent_id,
            level=data.level,
            sort_order=sort_order,
            title=data.title,
            summary=data.summary,
            notes=data.notes,
        )
        db.add(obj)
        db.commit()
        db.refresh(obj)
        logger.info("Created outline %s (project %s)", obj.id, obj.project_id)
        return obj

    @staticmethod
    def get(db: Session, outline_id: str) -> Outline | None:
        return db.query(Outline).filter(Outline.id == outline_id).first()

    @staticmethod
    def get_tree(db: Session, project_id: str) -> list[Outline]:
        return db.query(Outline).filter(
            Outline.project_id == project_id
        ).order_by(Outline.sort_order).all()

    @staticmethod
    def update(db: Session, outline_id: str, data: OutlineUpdate) -> Outline | None:
        obj = OutlineService.get(db, outline_id)
        if not obj:
            return None
        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(obj, field, value)
        db.commit()
        db.refresh(obj)
        return obj

    @staticmethod
    def delete(db: Session, outline_id: str) -> tuple[bool, int]:
        obj = OutlineService.get(db, outline_id)
        if not obj:
            logger.warning("Delete failed: outline %s not found", outline_id)
            return False, 0
        child_count = db.query(Outline).filter(Outline.parent_id == outline_id).count()
        db.query(Outline).filter(Outline.parent_id == outline_id).delete()
        db.delete(obj)
        db.commit()
        logger.info("Deleted outline %s (children %d)", outline_id, child_count)
        return True, child_count

    @staticmethod
    def reorder(db: Session, items: list[dict]) -> None:
        for item in items:
            db.query(Outline).filter(Outline.id == item["id"]).update(
                {"sort_order": item["sort_order"]}
            )
        db.commit()
