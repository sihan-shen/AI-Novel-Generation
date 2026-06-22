"""Unit tests for review/setting tools, agent config builders, and services."""

import json
from unittest.mock import patch

import pytest

from app.agents.agents.reviewer import build_reviewer_config
from app.agents.agents.settings_mgr import build_settings_mgr_config
from app.agents.agents.writer import build_writer_config
from app.agents.autonomy import AutonomyConfig
from app.agents.blackboard import Blackboard
from app.agents.tools.review import get_chapter_content, submit_review
from app.agents.tools.setting import (
    get_setting_detail,
    link_settings,
    propose_setting,
    search_settings,
)
from app.models.ai_call import AICall
from app.models.chapter import Chapter
from app.models.outline import Outline
from app.models.project import Project
from app.models.review import Review
from app.models.setting import Setting, SettingRelation
from app.services.outline_gen_service import OutlineGenerationService
from app.services.review_service import ReviewService
from app.services.setting_service import SettingService

# ---------------------------------------------------------------------------
# Tools / review.py
# ---------------------------------------------------------------------------

def test_get_chapter_content_found(db_session):
    """Given a chapter exists, when get_chapter_content is called,
    then it returns a JSON string with id, title, content, word_count."""
    db_session.add(Project(id="p1", title="Test Project"))
    db_session.add(Chapter(id="c1", project_id="p1", title="Ch1", content="Hello world", sort_order=1, word_count=2))
    db_session.commit()

    result = get_chapter_content(db_session, chapter_id="c1")
    data = json.loads(result)

    assert data["id"] == "c1"
    assert data["title"] == "Ch1"
    assert data["content"] == "Hello world"
    assert data["word_count"] == 2


def test_get_chapter_content_not_found(db_session):
    """Given a chapter does NOT exist, when get_chapter_content is called,
    then it returns a JSON string with an error message."""
    result = get_chapter_content(db_session, chapter_id="missing")
    data = json.loads(result)
    assert data["error"] == "Chapter not found"


def test_submit_review_creates_review_row(db_session):
    """Given a project and chapter exist, when submit_review is called,
    then it creates a Review row in the DB and returns the review_id."""
    db_session.add(Project(id="p1", title="Test Project"))
    db_session.add(Chapter(id="c1", project_id="p1", title="Ch1", content="Text", sort_order=1))
    db_session.commit()

    result = submit_review(
        db_session, project_id="p1", chapter_id="c1",
        overall_score=4.0, setting_score=3.5, style_score=4.0,
        logic_score=3.0, findings=["f1"], summary="summary",
        write_mode="draft", task_id="t1",
    )
    data = json.loads(result)

    assert data["status"] == "submitted"
    assert "review_id" in data

    review = db_session.query(Review).filter_by(id=data["review_id"]).first()
    assert review is not None
    assert review.project_id == "p1"
    assert review.chapter_id == "c1"
    assert review.scope == "agent"
    assert review.triggered_by_type == "agent"
    assert review.triggered_by_task_id == "t1"


# ---------------------------------------------------------------------------
# Tools / setting.py
# ---------------------------------------------------------------------------

def test_search_settings_no_filter(db_session):
    """Given active settings exist, when search_settings is called with no keywords,
    then it returns all active settings."""
    db_session.add(Project(id="p1", title="Test Project"))
    db_session.add(Setting(id="s1", project_id="p1", category="人物", name="Alice", key="alice", status="active"))
    db_session.add(Setting(id="s2", project_id="p1", category="地理", name="Beijing", key="beijing", status="active"))
    db_session.commit()

    result = search_settings(db_session, project_id="p1", keywords="")
    data = json.loads(result)

    assert len(data) == 2
    names = {s["name"] for s in data}
    assert names == {"Alice", "Beijing"}


def test_search_settings_with_keywords(db_session):
    """Given settings exist, when search_settings is called with keywords,
    then it returns only settings matching the keywords."""
    db_session.add(Project(id="p1", title="Test Project"))
    db_session.add(Setting(id="s1", project_id="p1", category="人物", name="Alice", summary="A girl", key="alice", status="active"))
    db_session.add(Setting(id="s2", project_id="p1", category="地理", name="Beijing", summary="A city", key="beijing", status="active"))
    db_session.commit()

    result = search_settings(db_session, project_id="p1", keywords="girl")
    data = json.loads(result)

    assert len(data) == 1
    assert data[0]["name"] == "Alice"


def test_search_settings_with_category(db_session):
    """Given settings in multiple categories, when search_settings filters by category,
    then it returns only settings in that category."""
    db_session.add(Project(id="p1", title="Test Project"))
    db_session.add(Setting(id="s1", project_id="p1", category="人物", name="Alice", key="alice", status="active"))
    db_session.add(Setting(id="s2", project_id="p1", category="地理", name="Beijing", key="beijing", status="active"))
    db_session.commit()

    result = search_settings(db_session, project_id="p1", keywords="", category="人物")
    data = json.loads(result)

    assert len(data) == 1
    assert data[0]["name"] == "Alice"


def test_get_setting_detail_found(db_session):
    """Given a setting exists, when get_setting_detail is called,
    then it returns a JSON string with full setting details."""
    db_session.add(Project(id="p1", title="Test Project"))
    db_session.add(Setting(id="s1", project_id="p1", category="人物", name="Alice", key="alice", summary="A girl", content="Details", weight=8, status="active"))
    db_session.commit()

    result = get_setting_detail(db_session, setting_id="s1")
    data = json.loads(result)

    assert data["id"] == "s1"
    assert data["name"] == "Alice"
    assert data["key"] == "alice"
    assert data["weight"] == 8


def test_get_setting_detail_not_found(db_session):
    """Given a setting does NOT exist, when get_setting_detail is called,
    then it returns a JSON string with an error message."""
    result = get_setting_detail(db_session, setting_id="missing")
    data = json.loads(result)
    assert data["error"] == "Setting not found"


def test_propose_setting_creates_new(db_session):
    """Given no setting with the key exists, when propose_setting is called in direct mode,
    then it creates a new Setting row."""
    db_session.add(Project(id="p1", title="Test Project"))
    db_session.commit()

    result = propose_setting(
        db_session, project_id="p1", category="人物", name="Bob",
        key="bob", summary="A boy", content="Details", weight=5,
        write_mode="direct", task_id="t1",
    )
    data = json.loads(result)

    assert data["status"] == "created"
    assert "setting_id" in data

    setting = db_session.query(Setting).filter_by(key="bob", project_id="p1").first()
    assert setting is not None
    assert setting.name == "Bob"
    assert setting.proposed_by_type == "agent"
    assert setting.proposed_by_task_id == "t1"


def test_propose_setting_updates_existing_by_key(db_session):
    """Given a setting with the same key exists, when propose_setting is called in direct mode,
    then it updates the existing setting instead of creating a duplicate."""
    db_session.add(Project(id="p1", title="Test Project"))
    db_session.add(Setting(id="s1", project_id="p1", category="人物", name="OldBob", key="bob", summary="Old", content="Old", weight=3))
    db_session.commit()

    result = propose_setting(
        db_session, project_id="p1", category="人物", name="NewBob",
        key="bob", summary="Updated", content="Updated details", weight=7,
        write_mode="direct", task_id="t1",
    )
    data = json.loads(result)

    assert data["status"] == "updated"
    assert data["setting_id"] == "s1"

    setting = db_session.query(Setting).filter_by(id="s1").first()
    assert setting.name == "NewBob"
    assert setting.weight == 7
    assert setting.proposed_by_type == "agent"


def test_link_settings_creates_relation(db_session):
    """Given two settings exist, when link_settings is called,
    then it creates a SettingRelation row."""
    db_session.add(Project(id="p1", title="Test Project"))
    db_session.add(Setting(id="s1", project_id="p1", category="人物", name="Alice", key="alice"))
    db_session.add(Setting(id="s2", project_id="p1", category="人物", name="Bob", key="bob"))
    db_session.commit()

    result = link_settings(db_session, from_setting_id="s1", to_setting_id="s2", relation_type="friend", description="Best friends")
    data = json.loads(result)

    assert data["status"] == "created"
    assert "relation_id" in data

    rel = db_session.query(SettingRelation).filter_by(from_setting_id="s1", to_setting_id="s2").first()
    assert rel is not None
    assert rel.relation_type == "friend"


# ---------------------------------------------------------------------------
# Agent config builders
# ---------------------------------------------------------------------------

def test_build_writer_config(db_session):
    """Given a blackboard, when build_writer_config is called,
    then it returns an AgentConfig with 8 tools and temperature 0.7."""
    bb = Blackboard(project_id="p1", task={"type": "writing"}, autonomy_config=AutonomyConfig())
    config = build_writer_config(db=db_session, project_id="p1", blackboard=bb)

    assert config.temperature == 0.7
    tool_names = {t.name for t in config.tools}
    expected = {
        "lookup_settings", "get_outline_context", "get_recent_chapters",
        "get_style_guide", "write_chapter", "update_outline_status",
        "search_any", "report_progress",
    }
    assert tool_names == expected
    assert len(config.tools) == 8


def test_build_reviewer_config(db_session):
    """Given a blackboard, when build_reviewer_config is called,
    then it returns an AgentConfig with the expected tools and temperature 0.3."""
    bb = Blackboard(project_id="p1", task={"type": "review"}, autonomy_config=AutonomyConfig())
    config = build_reviewer_config(db=db_session, project_id="p1", chapter_id="c1", blackboard=bb)

    assert config.temperature == 0.3
    tool_names = {t.name for t in config.tools}
    expected = {
        "get_chapter_content", "get_style_guide", "get_recent_chapters",
        "check_setting_consistency", "check_style_consistency",
        "check_logic_structure", "submit_review", "search_any",
    }
    assert tool_names == expected
    assert len(config.tools) == 8


def test_build_settings_mgr_config(db_session):
    """Given a blackboard, when build_settings_mgr_config is called,
    then it returns an AgentConfig with the expected tools and temperature 0.3."""
    bb = Blackboard(project_id="p1", task={"type": "settings"}, autonomy_config=AutonomyConfig())
    config = build_settings_mgr_config(db=db_session, project_id="p1", blackboard=bb)

    assert config.temperature == 0.3
    tool_names = {t.name for t in config.tools}
    expected = {
        "search_settings", "get_setting_detail", "get_related_settings",
        "propose_setting", "detect_conflicts", "resolve_conflict",
        "link_settings", "search_any",
    }
    assert tool_names == expected
    assert len(config.tools) == 8


# ---------------------------------------------------------------------------
# Services
# ---------------------------------------------------------------------------

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


@pytest.mark.asyncio
async def test_review_service_run_review_returns_4_dimensions(db_session):
    """Given a FakeAdapter returning 4-dimension JSON, when run_review is called,
    then it returns all 4 dimension scores and findings."""
    db_session.add(Project(id="p1", title="Test Project"))
    db_session.add(Chapter(id="c1", project_id="p1", title="Ch1", content="The wizard cast a spell.", sort_order=1))
    db_session.commit()

    adapter = FakeAdapter(json.dumps({
        "setting_consistency": {"score": 4.0, "findings": ["s1"]},
        "style_consistency": {"score": 3.5, "findings": ["s2"]},
        "logic_structure": {"score": 4.5, "findings": ["s3"]},
        "language_polish": {"score": 3.0, "findings": ["s4"]},
    }))

    with patch("app.services.review_service.get_adapter", return_value=adapter):
        chapter = db_session.query(Chapter).filter_by(id="c1").first()
        result = await ReviewService.run_review(db_session, chapter)

    assert "summary" in result
    assert "findings" in result
    dims = result["summary"]["dimensions"]
    assert len(dims) == 4
    assert dims["setting_consistency"]["score"] == 4.0
    assert dims["style_consistency"]["score"] == 3.5
    assert dims["logic_structure"]["score"] == 4.5
    assert dims["language_polish"]["score"] == 3.0
    assert adapter.call_count == 1

    # Verify AICall recorded
    calls = db_session.query(AICall).filter_by(scenario="review_run").all()
    assert len(calls) == 1
    assert calls[0].project_id == "p1"


def test_setting_service_build_llm_context_non_empty(db_session):
    """Given active settings exist, when build_llm_context is called,
    then it returns a non-empty string containing setting names and keys."""
    db_session.add(Project(id="p1", title="Test Project"))
    db_session.add(Setting(id="s1", project_id="p1", category="人物", name="Alice", key="alice", summary="A girl", weight=8, status="active"))
    db_session.add(Setting(id="s2", project_id="p1", category="地理", name="Beijing", key="beijing", summary="A city", weight=3, status="active"))
    db_session.commit()

    context = SettingService.build_llm_context(db_session, project_id="p1")

    assert isinstance(context, str)
    assert len(context) > 0
    assert "Alice" in context
    assert "alice" in context
    assert "Beijing" in context
    assert "beijing" in context


def test_outline_gen_confirm_save(db_session):
    """Given a list of outline items, when confirm_save is called,
    then it creates Outline rows and returns the saved count."""
    db_session.add(Project(id="p1", title="Test Project"))
    db_session.commit()

    items = [
        {
            "level": 1,
            "title": "Volume 1",
            "summary": "The beginning",
            "notes": "notes",
            "children": [
                {"level": 2, "title": "Chapter 1", "summary": "Intro", "notes": ""},
                {"level": 2, "title": "Chapter 2", "summary": "Rising", "notes": ""},
            ],
        },
        {"level": 1, "title": "Volume 2", "summary": "The end", "notes": ""},
    ]

    count = OutlineGenerationService.confirm_save(db_session, project_id="p1", items=items)
    assert count == 4

    outlines = db_session.query(Outline).filter_by(project_id="p1").all()
    assert len(outlines) == 4
    titles = {o.title for o in outlines}
    assert titles == {"Volume 1", "Chapter 1", "Chapter 2", "Volume 2"}

    # Verify parent-child linkage
    vol1 = db_session.query(Outline).filter_by(title="Volume 1").first()
    ch1 = db_session.query(Outline).filter_by(title="Chapter 1").first()
    assert ch1.parent_id == vol1.id


# ---------------------------------------------------------------------------
# Additional edge-case tests to hit >=15
# ---------------------------------------------------------------------------

def test_search_settings_inactive_excluded(db_session):
    """Given active and inactive settings, when search_settings is called,
    then inactive settings are excluded from results."""
    db_session.add(Project(id="p1", title="Test Project"))
    db_session.add(Setting(id="s1", project_id="p1", category="人物", name="Alice", key="alice", status="active"))
    db_session.add(Setting(id="s2", project_id="p1", category="人物", name="Bob", key="bob", status="archived"))
    db_session.commit()

    result = search_settings(db_session, project_id="p1", keywords="")
    data = json.loads(result)

    assert len(data) == 1
    assert data[0]["name"] == "Alice"


def test_propose_setting_suggest_mode_returns_suggestion(db_session):
    """Given suggest mode, when propose_setting is called,
    then it returns a suggested status without creating a DB row."""
    db_session.add(Project(id="p1", title="Test Project"))
    db_session.commit()

    result = propose_setting(
        db_session, project_id="p1", category="人物", name="Charlie",
        key="charlie", summary="A char", write_mode="suggest",
    )
    data = json.loads(result)

    assert data["status"] == "suggested"
    assert db_session.query(Setting).filter_by(key="charlie").first() is None


@pytest.mark.asyncio
async def test_review_service_run_review_fallback_on_bad_json(db_session):
    """Given a FakeAdapter returning non-JSON, when run_review is called,
    then it falls back to stub scores for all 4 dimensions."""
    db_session.add(Project(id="p1", title="Test Project"))
    db_session.add(Chapter(id="c1", project_id="p1", title="Ch1", content="Text", sort_order=1))
    db_session.commit()

    adapter = FakeAdapter("not valid json")

    with patch("app.services.review_service.get_adapter", return_value=adapter):
        chapter = db_session.query(Chapter).filter_by(id="c1").first()
        result = await ReviewService.run_review(db_session, chapter)

    dims = result["summary"]["dimensions"]
    assert len(dims) == 4
    for dim in ReviewService.DIMENSIONS:
        assert dim in dims
        assert dims[dim]["score"] == 3.5  # fallback default


def test_setting_service_build_llm_context_with_related_ids(db_session):
    """Given settings and related_ids, when build_llm_context is called,
    then the context includes detailed sections for related settings."""
    db_session.add(Project(id="p1", title="Test Project"))
    db_session.add(Setting(id="s1", project_id="p1", category="人物", name="Alice", key="alice", summary="A girl", content="Long content about Alice", weight=8, status="active"))
    db_session.add(Setting(id="s2", project_id="p1", category="地理", name="Beijing", key="beijing", summary="A city", weight=3, status="active"))
    db_session.commit()

    context = SettingService.build_llm_context(db_session, project_id="p1", related_ids=["s1"])

    assert "详细设定" in context
    assert "Alice" in context
    assert "A girl" in context
