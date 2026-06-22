import json as j
import logging
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.response import APIResponse
from app.services.review_service import ReviewService

logger = logging.getLogger(__name__)


class ReviewResponse(BaseModel):
    id: str
    project_id: str
    chapter_id: str | None
    scope: str
    summary: str
    findings: str
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


router = APIRouter(prefix="/api/projects/{project_id}/reviews", tags=["reviews"])


@router.get("", response_model=APIResponse[list[ReviewResponse]])
async def list_reviews(project_id: str, db: Session = Depends(get_db)):
    reviews = ReviewService.list_reviews(db, project_id)
    return APIResponse(data=reviews)


@router.get("/{review_id}", response_model=APIResponse[dict])
async def get_review(review_id: str, project_id: str, db: Session = Depends(get_db)):
    review = ReviewService.get_review(db, review_id)
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")
    findings = []
    if review.findings and review.findings != "[]":
        try:
            findings = j.loads(review.findings)
        except (j.JSONDecodeError, ValueError):
            findings = []
    summary = {}
    if review.summary and review.summary != "{}":
        try:
            summary = j.loads(review.summary)
        except (j.JSONDecodeError, ValueError):
            summary = {}
    return APIResponse(
        data={"review": ReviewResponse.model_validate(review), "findings": findings, "summary": summary}  # noqa: E501
    )
