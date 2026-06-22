import logging

from sqlalchemy.orm import Session

from app.models.project import Project
from app.schemas.project import ProjectCreate, ProjectUpdate

logger = logging.getLogger(__name__)


class ProjectService:
    @staticmethod
    def create(db: Session, data: ProjectCreate) -> Project:
        project = Project(title=data.title, description=data.description, genre=data.genre)
        db.add(project)
        db.commit()
        db.refresh(project)
        logger.info("Created project %s", project.id)
        return project

    @staticmethod
    def get(db: Session, project_id: str) -> Project | None:
        return db.query(Project).filter(Project.id == project_id).first()

    @staticmethod
    def list(db: Session) -> list[Project]:
        return db.query(Project).order_by(Project.updated_at.desc()).all()

    @staticmethod
    def update(db: Session, project_id: str, data: ProjectUpdate) -> Project | None:
        project = ProjectService.get(db, project_id)
        if not project:
            return None
        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(project, field, value)
        db.commit()
        db.refresh(project)
        return project

    @staticmethod
    def delete(db: Session, project_id: str) -> bool:
        project = ProjectService.get(db, project_id)
        if not project:
            logger.warning("Delete failed: project %s not found", project_id)
            return False
        db.delete(project)
        db.commit()
        logger.info("Deleted project %s", project_id)
        return True
