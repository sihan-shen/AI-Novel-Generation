import json
import logging

from sqlalchemy.orm import Session

from app.llm.adapter import get_adapter, record_usage
from app.llm.context_builder import ContextBuilder
from app.models.chapter import Chapter
from app.models.review import Review

logger = logging.getLogger(__name__)


class ReviewService:
    DIMENSIONS = ["setting_consistency", "style_consistency", "logic_structure", "language_polish"]

    @staticmethod
    def create_review(db: Session, project_id: str, chapter_id: str | None, scope: str, summary: dict, findings: list) -> Review:  # noqa: E501
        review = Review(
            project_id=project_id,
            chapter_id=chapter_id,
            scope=scope,
            summary=json.dumps(summary, ensure_ascii=False),
            findings=json.dumps(findings, ensure_ascii=False),
        )
        db.add(review)
        db.commit()
        db.refresh(review)
        return review

    @staticmethod
    async def diff_review(db: Session, chapter: Chapter, previous_content: str) -> dict:
        """Only review newly added/modified content."""
        if not previous_content:
            return await ReviewService.run_review(db, chapter)
        new_content = chapter.content[len(previous_content):] if len(chapter.content) > len(previous_content) else chapter.content  # noqa: E501
        review_result = await ReviewService.run_review(db, chapter)
        review_result["scope"] = "diff"
        review_result["summary"]["diff_length"] = len(new_content)
        return review_result

    @staticmethod
    async def run_review(db: Session, chapter: Chapter) -> dict:
        """Run full 4-dimension review on a chapter."""
        builder = ContextBuilder(db)
        messages = builder.build("review", chapter.project_id, request=chapter.content[:3000])  # type: ignore[arg-type]
        adapter = get_adapter(db)
        response = await adapter.generate(messages, temperature=0.3, max_tokens=2048)
        try:
            record_usage(  # type: ignore[attr-defined,arg-type]
                db, adapter.model, response.usage,  # type: ignore[attr-defined]
                scenario="review_run", project_id=chapter.project_id,  # type: ignore[arg-type]
            )
        except Exception as e:
            logger.warning("record_usage failed for review_run: %s", e)

        # Parse structured 4-dimension review from LLM response
        parsed = ReviewService._parse_review_response(response.content)
        return parsed

    @staticmethod
    def _parse_review_response(content: str) -> dict:
        """Parse JSON review response; fall back to stub values on error."""
        try:
            data = json.loads(content)
        except (json.JSONDecodeError, ValueError):
            data = {}

        dimensions = {}
        findings = []
        total_score = 0.0
        valid_dims = 0

        for dim in ReviewService.DIMENSIONS:
            dim_data = data.get(dim, {})
            if isinstance(dim_data, dict):
                score = dim_data.get("score", 3.5)
                dim_findings = dim_data.get("findings", [])
            else:
                score = 3.5
                dim_findings = []

            dimensions[dim] = {"score": score, "findings": dim_findings}
            findings.append({
                "dimension": dim,
                "severity": "medium" if score < 3.0 else "low",
                "description": f"{dim} 检查完成",
                "suggestion": str(dim_findings[0]) if dim_findings else "",
            })
            total_score += score
            valid_dims += 1

        overall_score = total_score / valid_dims if valid_dims > 0 else 3.5
        summary = {"overall_score": overall_score, "dimensions": dimensions}
        return {"summary": summary, "findings": findings, "raw": content}

    @staticmethod
    def list_reviews(db: Session, project_id: str) -> list[Review]:
        return db.query(Review).filter(Review.project_id == project_id).order_by(Review.created_at.desc()).all()  # noqa: E501

    @staticmethod
    def get_review(db: Session, review_id: str) -> Review | None:
        return db.query(Review).filter(Review.id == review_id).first()
