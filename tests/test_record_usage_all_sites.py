import json
from unittest.mock import patch

import pytest

from app.llm.adapter import LLMResponse
from app.models.ai_call import AICall
from app.models.chapter import Chapter
from app.models.project import Project
from app.services.cleaning_service import CleaningService
from app.services.outline_gen_service import OutlineGenerationService
from app.services.review_service import ReviewService
from app.services.style_service import StyleService


class FakeAdapter:
    """Mock LLM adapter that returns predetermined responses and supports usage_callback."""

    def __init__(self, content: str | None = None, usage: dict | None = None):
        self.content = content or "{}"
        self.usage = usage or {"input_tokens": 10, "output_tokens": 5}
        self.model = "test-model"
        self.stream_chunks: list[str] = []
        self.usage_callback_called = False

    async def generate(self, messages, **kwargs):
        return LLMResponse(content=self.content, usage=self.usage)

    async def generate_stream(self, messages, **kwargs):
        usage_callback = kwargs.get("usage_callback")
        for chunk in self.stream_chunks:
            yield chunk
        if usage_callback is not None:
            usage_callback(self.usage)
            self.usage_callback_called = True

    def count_tokens(self, text: str) -> int:
        return len(text) // 4


def _seed_project(db_session, project_id="p1"):
    db_session.add(Project(id=project_id, title="Test", description="", genre=""))
    db_session.commit()


@pytest.mark.asyncio
async def test_style_analyze_records_usage(db_session):
    """Given a FakeAdapter, when StyleService.analyze_text is called,
    then an AICall row exists with scenario='style_analyze' and project_id set."""
    _seed_project(db_session)
    adapter = FakeAdapter(content='{"vocabulary":"rich"}')

    with patch("app.services.style_service.get_adapter", return_value=adapter):
        result = await StyleService.analyze_text(db_session, "some text", project_id="p1")

    assert result == '{"vocabulary":"rich"}'
    calls = db_session.query(AICall).filter(AICall.scenario == "style_analyze").all()
    assert len(calls) == 1
    assert calls[0].project_id == "p1"
    assert calls[0].model == "test-model"
    assert calls[0].input_tokens == 10
    assert calls[0].output_tokens == 5


@pytest.mark.asyncio
async def test_style_smart_slice_records_usage(db_session):
    """Given a FakeAdapter, when StyleService.smart_slice is called,
    then an AICall row exists with scenario='style_slice' and project_id set."""
    _seed_project(db_session)
    adapter = FakeAdapter(content='{"slices":[{"text":"slice1","reason":"r","stars":5}]}')

    with patch("app.services.style_service.get_adapter", return_value=adapter):
        result = await StyleService.smart_slice(db_session, "long text here", project_id="p1")

    assert len(result) == 1
    calls = db_session.query(AICall).filter(AICall.scenario == "style_slice").all()
    assert len(calls) == 1
    assert calls[0].project_id == "p1"


@pytest.mark.asyncio
async def test_cleaning_consistency_check_records_usage(db_session):
    """Given a FakeAdapter, when CleaningService.consistency_check is called,
    then an AICall row exists with scenario='cleaning_check' and project_id set."""
    _seed_project(db_session)
    adapter = FakeAdapter(content='{"contradictions":[],"duplicates":[]}')

    with patch("app.services.cleaning_service.get_adapter", return_value=adapter):
        result = await CleaningService.consistency_check(db_session, project_id="p1")

    assert "contradictions" in result
    calls = db_session.query(AICall).filter(AICall.scenario == "cleaning_check").all()
    assert len(calls) == 1
    assert calls[0].project_id == "p1"


@pytest.mark.asyncio
async def test_outline_gen_volumes_stream_records_usage(db_session):
    """Given a FakeAdapter with stream support, when generate_volumes_stream is consumed,
    then an AICall row exists with scenario='outline_gen_volumes' and project_id set."""
    _seed_project(db_session)
    adapter = FakeAdapter()
    adapter.stream_chunks = ["vol1", "vol2"]

    with patch("app.services.outline_gen_service.get_adapter", return_value=adapter):
        chunks = []
        async for chunk in OutlineGenerationService.generate_volumes_stream(db_session, "p1", "desc"):
            chunks.append(chunk)

    assert chunks == ["vol1", "vol2"]
    assert adapter.usage_callback_called is True
    calls = db_session.query(AICall).filter(AICall.scenario == "outline_gen_volumes").all()
    assert len(calls) == 1
    assert calls[0].project_id == "p1"


@pytest.mark.asyncio
async def test_outline_gen_chapters_stream_records_usage(db_session):
    """Given a FakeAdapter with stream support, when generate_chapters_stream is consumed,
    then an AICall row exists with scenario='outline_gen_chapters'."""
    _seed_project(db_session)
    adapter = FakeAdapter()
    adapter.stream_chunks = ["ch1"]

    with patch("app.services.outline_gen_service.get_adapter", return_value=adapter):
        chunks = []
        async for chunk in OutlineGenerationService.generate_chapters_stream(db_session, "p1", "V", "S"):
            chunks.append(chunk)

    calls = db_session.query(AICall).filter(AICall.scenario == "outline_gen_chapters").all()
    assert len(calls) == 1


@pytest.mark.asyncio
async def test_outline_gen_sections_stream_records_usage(db_session):
    """Given a FakeAdapter with stream support, when generate_sections_stream is consumed,
    then an AICall row exists with scenario='outline_gen_sections'."""
    _seed_project(db_session)
    adapter = FakeAdapter()
    adapter.stream_chunks = ["sec1"]

    with patch("app.services.outline_gen_service.get_adapter", return_value=adapter):
        chunks = []
        async for chunk in OutlineGenerationService.generate_sections_stream(db_session, "p1", "C", "S"):
            chunks.append(chunk)

    calls = db_session.query(AICall).filter(AICall.scenario == "outline_gen_sections").all()
    assert len(calls) == 1


@pytest.mark.asyncio
async def test_outline_gen_content_stream_records_usage(db_session):
    """Given a FakeAdapter with stream support, when generate_content_stream is consumed,
    then an AICall row exists with scenario='outline_gen_content'."""
    _seed_project(db_session)
    adapter = FakeAdapter()
    adapter.stream_chunks = ["content"]

    with patch("app.services.outline_gen_service.get_adapter", return_value=adapter):
        chunks = []
        async for chunk in OutlineGenerationService.generate_content_stream(db_session, "p1", "T", []):
            chunks.append(chunk)

    calls = db_session.query(AICall).filter(AICall.scenario == "outline_gen_content").all()
    assert len(calls) == 1


@pytest.mark.asyncio
async def test_review_run_records_usage_and_returns_four_dimensions(db_session):
    """Given a FakeAdapter returning 4-dimension JSON, when ReviewService.run_review is called,
    then an AICall row exists with scenario='review_run', project_id set,
    and the result contains all 4 dimensions with computed overall_score."""
    _seed_project(db_session)
    db_session.add(Chapter(id="c1", project_id="p1", title="Ch1", content="content", sort_order=0))
    db_session.commit()

    review_json = {
        "setting_consistency": {"score": 4.0, "findings": ["f1"]},
        "style_consistency": {"score": 3.5, "findings": ["f2"]},
        "logic_structure": {"score": 4.5, "findings": ["f3"]},
        "language_polish": {"score": 3.0, "findings": ["f4"]},
    }
    adapter = FakeAdapter(content=json.dumps(review_json))

    with patch("app.services.review_service.get_adapter", return_value=adapter):
        chapter = db_session.query(Chapter).filter(Chapter.id == "c1").first()
        result = await ReviewService.run_review(db_session, chapter)

    calls = db_session.query(AICall).filter(AICall.scenario == "review_run").all()
    assert len(calls) == 1
    assert calls[0].project_id == "p1"

    summary = result["summary"]
    assert "overall_score" in summary
    assert summary["overall_score"] == 3.75  # average of 4.0, 3.5, 4.5, 3.0
    dims = summary["dimensions"]
    assert len(dims) == 4
    assert dims["setting_consistency"]["score"] == 4.0
    assert dims["style_consistency"]["score"] == 3.5
    assert dims["logic_structure"]["score"] == 4.5
    assert dims["language_polish"]["score"] == 3.0

    findings = result["findings"]
    assert len(findings) == 4
    dim_names = {f["dimension"] for f in findings}
    assert dim_names == {"setting_consistency", "style_consistency", "logic_structure", "language_polish"}


@pytest.mark.asyncio
async def test_review_run_json_parse_error_falls_back_to_stub(db_session):
    """Given a FakeAdapter returning invalid JSON, when ReviewService.run_review is called,
    then it falls back to stub values without crashing."""
    _seed_project(db_session)
    db_session.add(Chapter(id="c1", project_id="p1", title="Ch1", content="content", sort_order=0))
    db_session.commit()

    adapter = FakeAdapter(content="not json")

    with patch("app.services.review_service.get_adapter", return_value=adapter):
        chapter = db_session.query(Chapter).filter(Chapter.id == "c1").first()
        result = await ReviewService.run_review(db_session, chapter)

    # Should not crash; returns fallback with 4 dimensions
    summary = result["summary"]
    assert "overall_score" in summary
    assert summary["overall_score"] == 3.5
    dims = summary["dimensions"]
    assert len(dims) == 4
    findings = result["findings"]
    assert len(findings) == 4


@pytest.mark.asyncio
async def test_style_analyze_record_usage_failure_continues(db_session, caplog):
    """Given record_usage raises, when analyze_text runs,
    then the service continues and returns the LLM result."""
    import logging
    caplog.set_level(logging.WARNING)
    _seed_project(db_session)
    adapter = FakeAdapter(content='{"vocabulary":"rich"}')

    with patch("app.services.style_service.get_adapter", return_value=adapter):
        with patch("app.services.style_service.record_usage", side_effect=RuntimeError("db boom")):
            result = await StyleService.analyze_text(db_session, "text", project_id="p1")

    assert result == '{"vocabulary":"rich"}'
    assert any("record_usage failed" in r.message for r in caplog.records)
