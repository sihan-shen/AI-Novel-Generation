import logging

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.services.search_service import SearchService

logger = logging.getLogger(__name__)


router = APIRouter(prefix="/api", tags=["search"])

VALID_TYPES = {"all", "project", "chapter", "outline", "setting", "idea"}


@router.get("/search")
async def search(
    q: str = Query(""),
    type: str = Query("all"),
    limit: int = Query(50, ge=1, le=200),
    project_id: str | None = Query(None),
    db: Session = Depends(get_db),
):
    if type not in VALID_TYPES:
        return {"results": [], "total": 0}
    results = SearchService.search(db, q=q, type=type, limit=limit, project_id=project_id)
    return {"results": results, "total": len(results)}
