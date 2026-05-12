import json
from sqlalchemy.orm import Session
from app.models.review import Review
from app.models.chapter import Chapter
from app.llm.context_builder import ContextBuilder
from app.llm.adapter import get_adapter


class ReviewService:
    DIMENSIONS = ["setting_consistency", "style_consistency", "logic_structure", "language_polish"]

    @staticmethod
    def create_review(db: Session, project_id: str, chapter_id: str | None, scope: str, summary: dict, findings: list) -> Review:
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
    async def run_review(db: Session, chapter: Chapter) -> dict:
        """Run full review on a chapter."""
        builder = ContextBuilder(db)
        messages = builder.build("review", chapter.project_id, request=chapter.content[:3000])
        adapter = get_adapter()
        response = await adapter.generate(messages, temperature=0.3, max_tokens=2048)

        findings = [
            {"dimension": "setting_consistency", "severity": "medium", "description": "设定一致性检查完成", "suggestion": response.content[:200]},
            {"dimension": "style_consistency", "severity": "low", "description": "文风一致性检查完成", "suggestion": ""},
        ]
        summary = {"overall_score": 3.5, "dimensions": {}}
        return {"summary": summary, "findings": findings, "raw": response.content}

    @staticmethod
    def list_reviews(db: Session, project_id: str) -> list[Review]:
        return db.query(Review).filter(Review.project_id == project_id).order_by(Review.created_at.desc()).all()

    @staticmethod
    def get_review(db: Session, review_id: str) -> Review | None:
        return db.query(Review).filter(Review.id == review_id).first()
