import logging

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.models.chapter import Chapter
from app.models.idea import Idea
from app.models.outline import Outline
from app.models.project import Project
from app.models.setting import Setting

logger = logging.getLogger(__name__)


def _snippet(text: str, q: str, width: int = 80) -> str:
    if not text:
        return ""
    text = str(text)
    if not q:
        return text[:width]
    lower_text = text.lower()
    idx = lower_text.find(q.lower())
    if idx < 0:
        return text[:width]
    start = max(0, idx - width // 2)
    return text[start : start + width]


class SearchService:
    @staticmethod
    def search(db: Session, q: str, type: str = "all", limit: int = 50, project_id: str | None = None) -> list[dict]:  # noqa: E501
        q = (q or "").strip()
        like = f"%{q}%" if q else "%"
        results: list[dict] = []
        project_titles: dict[str, str] = {p.id: p.title for p in db.query(Project).all()}  # type: ignore[misc]
        logger.info("Search query=%s type=%s project=%s", q, type, project_id)

        type_handlers = {
            "project": SearchService._search_projects,
            "chapter": SearchService._search_chapters,
            "outline": SearchService._search_outlines,
            "setting": SearchService._search_settings,
            "idea": SearchService._search_ideas,
        }

        if type == "all":
            for handler in type_handlers.values():
                results.extend(handler(db, q, like, project_titles, project_id))
        elif type in type_handlers:
            results.extend(type_handlers[type](db, q, like, project_titles, project_id))

        return results[:limit]

    @staticmethod
    def _search_projects(db, q, like, project_titles, project_id):
        query = db.query(Project).filter(or_(Project.title.ilike(like), Project.description.ilike(like)))  # noqa: E501
        return [{
            "type": "project",
            "id": p.id,
            "title": p.title,
            "snippet": _snippet(p.description, q),
            "project_id": p.id,
            "project_title": None,
        } for p in query.all()]

    @staticmethod
    def _search_chapters(db, q, like, project_titles, project_id):
        query = db.query(Chapter).filter(or_(Chapter.title.ilike(like), Chapter.content.ilike(like)))  # noqa: E501
        if project_id:
            query = query.filter(Chapter.project_id == project_id)
        return [{
            "type": "chapter",
            "id": c.id,
            "title": c.title,
            "snippet": _snippet(c.content, q),
            "project_id": c.project_id,
            "project_title": project_titles.get(c.project_id),
        } for c in query.all()]

    @staticmethod
    def _search_outlines(db, q, like, project_titles, project_id):
        query = db.query(Outline).filter(or_(Outline.title.ilike(like), Outline.summary.ilike(like)))  # noqa: E501
        if project_id:
            query = query.filter(Outline.project_id == project_id)
        return [{
            "type": "outline",
            "id": o.id,
            "title": o.title,
            "snippet": _snippet(o.summary, q),
            "project_id": o.project_id,
            "project_title": project_titles.get(o.project_id),
        } for o in query.all()]

    @staticmethod
    def _search_settings(db, q, like, project_titles, project_id):
        # Setting uses `name`, `summary`, `content` (no `title` column)
        query = db.query(Setting).filter(or_(
            Setting.name.ilike(like),
            Setting.summary.ilike(like),
            Setting.content.ilike(like),
        ))
        if project_id:
            query = query.filter(Setting.project_id == project_id)
        return [{
            "type": "setting",
            "id": s.id,
            "title": s.name,
            "snippet": _snippet(s.summary or s.content, q),
            "project_id": s.project_id,
            "project_title": project_titles.get(s.project_id),
        } for s in query.all()]

    @staticmethod
    def _search_ideas(db, q, like, project_titles, project_id):
        query = db.query(Idea).filter(or_(Idea.title.ilike(like), Idea.content.ilike(like)))
        if project_id:
            query = query.filter(Idea.project_id == project_id)
        return [{
            "type": "idea",
            "id": i.id,
            "title": i.title or (i.content or "")[:40],
            "snippet": _snippet(i.content, q),
            "project_id": i.project_id,
            "project_title": project_titles.get(i.project_id),
        } for i in query.all()]
