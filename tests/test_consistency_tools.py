import json
from unittest.mock import patch

from app.agents.tools.review import (
    check_logic_structure,
    check_setting_consistency,
    check_style_consistency,
)
from app.models.ai_call import AICall
from app.models.chapter import Chapter
from app.models.project import Project
from app.models.setting import Setting
from app.models.style import ProjectStyleLink, Style


class FakeAdapter:
    """Fake LLM adapter returning predetermined JSON string responses."""
    def __init__(self, content: str):
        self.content = content
        self.model = "fake-model"
        self.call_count = 0

    async def generate(self, messages, **kwargs):
        from app.llm.adapter import LLMResponse
        self.call_count += 1
        return LLMResponse(
            content=self.content,
            usage={"input_tokens": 50, "output_tokens": 30},
        )

    def count_tokens(self, text):
        return 100


def _make_project_and_chapter(db_session):
    db_session.add(Project(id="p1", title="Test Project"))
    db_session.add(Chapter(id="c1", project_id="p1", title="Ch1", content="The wizard cast a spell.", sort_order=1))
    db_session.commit()


def test_check_setting_consistency_returns_structured_findings(db_session):
    """Given a FakeAdapter returning structured JSON, when check_setting_consistency is called,
    then it returns a dict with score, findings, and summary — NOT preview_ready."""
    _make_project_and_chapter(db_session)
    db_session.add(Setting(id="s1", project_id="p1", category="魔法", name="魔法体系", summary="古老魔法", content="魔力有限", key="magic", status="active"))
    db_session.commit()

    adapter = FakeAdapter(json.dumps({"score": 3.5, "findings": ["f1"], "summary": "ok"}))

    with patch("app.agents.tools.review.get_adapter", return_value=adapter):
        result = check_setting_consistency(db_session, chapter_id="c1", project_id="p1")

    assert isinstance(result, dict)
    assert "score" in result
    assert result["score"] == 3.5
    assert "findings" in result
    assert result["findings"] == ["f1"]
    assert "summary" in result
    assert result["summary"] == "ok"
    assert "preview_ready" not in result
    assert adapter.call_count == 1


def test_check_style_consistency_returns_structured_findings(db_session):
    """Given a FakeAdapter returning structured JSON, when check_style_consistency is called,
    then it returns a dict with score, findings, and summary — NOT 'ready'."""
    _make_project_and_chapter(db_session)
    db_session.add(Style(id="st1", name="古风", analysis='{"tone": "古典"}'))
    db_session.add(ProjectStyleLink(project_id="p1", style_id="st1", weight=80))
    db_session.commit()

    adapter = FakeAdapter(json.dumps({"score": 4.0, "findings": ["style-f1"], "summary": "style ok"}))

    with patch("app.agents.tools.review.get_adapter", return_value=adapter):
        result = check_style_consistency(db_session, chapter_id="c1", project_id="p1")

    assert isinstance(result, dict)
    assert result["score"] == 4.0
    assert result["findings"] == ["style-f1"]
    assert result["summary"] == "style ok"
    assert "ready" not in result
    assert adapter.call_count == 1


def test_check_logic_structure_returns_structured_findings(db_session):
    """Given a FakeAdapter returning structured JSON, when check_logic_structure is called,
    then it returns a dict with score, findings, and summary — NOT 'ready'."""
    _make_project_and_chapter(db_session)
    db_session.add(Chapter(id="c2", project_id="p1", title="Ch2", content="The dragon attacked.", sort_order=2))
    db_session.commit()

    adapter = FakeAdapter(json.dumps({"score": 2.5, "findings": ["logic-f1"], "summary": "logic ok"}))

    with patch("app.agents.tools.review.get_adapter", return_value=adapter):
        result = check_logic_structure(db_session, chapter_id="c1", project_id="p1")

    assert isinstance(result, dict)
    assert result["score"] == 2.5
    assert result["findings"] == ["logic-f1"]
    assert result["summary"] == "logic ok"
    assert "ready" not in result
    assert adapter.call_count == 1


def test_check_setting_consistency_records_ai_call(db_session):
    """Given a FakeAdapter, when check_setting_consistency is called,
    then an AICall row is written with scenario='check_setting_consistency'."""
    _make_project_and_chapter(db_session)
    adapter = FakeAdapter(json.dumps({"score": 3.0, "findings": [], "summary": "fine"}))

    with patch("app.agents.tools.review.get_adapter", return_value=adapter):
        check_setting_consistency(db_session, chapter_id="c1", project_id="p1")

    calls = db_session.query(AICall).all()
    assert len(calls) == 1
    assert calls[0].scenario == "check_setting_consistency"
    assert calls[0].project_id == "p1"
    assert calls[0].model == "fake-model"


def test_check_style_consistency_records_ai_call(db_session):
    """Given a FakeAdapter, when check_style_consistency is called,
    then an AICall row is written with scenario='check_style_consistency'."""
    _make_project_and_chapter(db_session)
    adapter = FakeAdapter(json.dumps({"score": 3.0, "findings": [], "summary": "fine"}))

    with patch("app.agents.tools.review.get_adapter", return_value=adapter):
        check_style_consistency(db_session, chapter_id="c1", project_id="p1")

    calls = db_session.query(AICall).filter_by(scenario="check_style_consistency").all()
    assert len(calls) == 1


def test_check_logic_structure_records_ai_call(db_session):
    """Given a FakeAdapter, when check_logic_structure is called,
    then an AICall row is written with scenario='check_logic_consistency'."""
    _make_project_and_chapter(db_session)
    adapter = FakeAdapter(json.dumps({"score": 3.0, "findings": [], "summary": "fine"}))

    with patch("app.agents.tools.review.get_adapter", return_value=adapter):
        check_logic_structure(db_session, chapter_id="c1", project_id="p1")

    calls = db_session.query(AICall).filter_by(scenario="check_logic_consistency").all()
    assert len(calls) == 1


def test_check_setting_consistency_non_json_returns_error_dict(db_session):
    """Given a FakeAdapter returning non-JSON, when check_setting_consistency is called,
    then it returns a fallback dict with score=0 and summary='LLM parse error', without crashing."""
    _make_project_and_chapter(db_session)
    adapter = FakeAdapter("not valid json")

    with patch("app.agents.tools.review.get_adapter", return_value=adapter):
        result = check_setting_consistency(db_session, chapter_id="c1", project_id="p1")

    assert isinstance(result, dict)
    assert result["dimension"] == "setting"
    assert result["score"] == 0
    assert result["findings"] == []
    assert result["summary"] == "LLM parse error"


def test_check_style_consistency_non_json_returns_error_dict(db_session):
    """Given a FakeAdapter returning non-JSON, when check_style_consistency is called,
    then it returns a fallback dict with score=0 and summary='LLM parse error'."""
    _make_project_and_chapter(db_session)
    adapter = FakeAdapter("not valid json")

    with patch("app.agents.tools.review.get_adapter", return_value=adapter):
        result = check_style_consistency(db_session, chapter_id="c1", project_id="p1")

    assert result["dimension"] == "style"
    assert result["score"] == 0
    assert result["findings"] == []
    assert result["summary"] == "LLM parse error"


def test_check_logic_structure_non_json_returns_error_dict(db_session):
    """Given a FakeAdapter returning non-JSON, when check_logic_structure is called,
    then it returns a fallback dict with score=0 and summary='LLM parse error'."""
    _make_project_and_chapter(db_session)
    adapter = FakeAdapter("not valid json")

    with patch("app.agents.tools.review.get_adapter", return_value=adapter):
        result = check_logic_structure(db_session, chapter_id="c1", project_id="p1")

    assert result["dimension"] == "logic"
    assert result["score"] == 0
    assert result["findings"] == []
    assert result["summary"] == "LLM parse error"


def test_check_setting_consistency_missing_chapter(db_session):
    """Given a missing chapter_id, when check_setting_consistency is called,
    then it returns an error dict immediately without calling the LLM."""
    adapter = FakeAdapter(json.dumps({"score": 5.0, "findings": [], "summary": "n/a"}))

    with patch("app.agents.tools.review.get_adapter", return_value=adapter):
        result = check_setting_consistency(db_session, chapter_id="missing", project_id="p1")

    assert "error" in result
    assert adapter.call_count == 0
