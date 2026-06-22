import json

from app.agents.tools.setting import detect_conflicts, resolve_conflict
from app.models.agent_task import AgentTask
from app.models.project import Project
from app.models.setting import Setting


class FakeAdapter:
    def __init__(self, responses: list[dict]):
        self.responses = responses
        self.call_count = 0

    async def generate(self, messages, **kwargs):
        resp = self.responses[self.call_count % len(self.responses)]
        self.call_count += 1
        from app.llm.adapter import LLMResponse
        return LLMResponse(
            content=json.dumps(resp),
            usage={"input_tokens": 100, "output_tokens": 50},
        )

    def count_tokens(self, text):
        return 100


def test_detect_conflicts_duplicate_key_no_llm(db_session):
    db_session.add(Project(id="p1", title="Test Project"))
    db_session.add(Setting(id="s1", project_id="p1", category="人物", name="Hero", key="hero", content="A brave knight", status="active"))
    db_session.add(Setting(id="s2", project_id="p1", category="人物", name="Protagonist", key="hero", content="A cowardly thief", status="active"))
    db_session.commit()

    result = json.loads(detect_conflicts(db_session, "p1", ["s1", "s2"]))
    assert len(result["conflicts"]) >= 1
    assert any("hero" in c["desc"].lower() or "duplicate" in c["desc"].lower() for c in result["conflicts"])


def test_detect_conflicts_no_conflicts(db_session):
    db_session.add(Project(id="p1", title="Test Project"))
    db_session.add(Setting(id="s1", project_id="p1", category="人物", name="Hero", key="hero", content="A brave knight", status="active"))
    db_session.add(Setting(id="s2", project_id="p1", category="世界观", name="Magic", key="magic", content="Ancient magic system", status="active"))
    db_session.commit()

    result = json.loads(detect_conflicts(db_session, "p1", ["s1", "s2"]))
    assert result == {"conflicts": []}


def test_detect_conflicts_llm_contradiction(db_session, monkeypatch):
    db_session.add(Project(id="p1", title="Test Project"))
    db_session.add(Setting(id="s1", project_id="p1", category="世界观", name="Gravity", key="gravity", content="Gravity is weak on this planet", status="active"))
    db_session.add(Setting(id="s2", project_id="p1", category="世界观", name="Combat", key="combat", content="Fighters can leap 50 meters because gravity is strong", status="active"))
    db_session.commit()

    fake_adapter = FakeAdapter([{
        "conflicts": [
            {"id": "c1", "desc": "Gravity strength contradiction", "severity": "high", "setting_ids": ["s1", "s2"]}
        ]
    }])

    monkeypatch.setattr("app.agents.tools.setting.get_adapter", lambda db=None: fake_adapter)

    result = json.loads(detect_conflicts(db_session, "p1", ["s1", "s2"]))
    assert len(result["conflicts"]) >= 1
    conflict = result["conflicts"][0]
    assert conflict["id"] == "c1"
    assert conflict["severity"] == "high"
    assert "s1" in conflict["setting_ids"] and "s2" in conflict["setting_ids"]


def test_detect_conflicts_llm_json_parse_error_fallback(db_session, monkeypatch):
    db_session.add(Project(id="p1", title="Test Project"))
    db_session.add(Setting(id="s1", project_id="p1", category="人物", name="Hero", key="hero", content="A brave knight", status="active"))
    db_session.add(Setting(id="s2", project_id="p1", category="人物", name="Villain", key="hero", content="A dark lord", status="active"))
    db_session.commit()

    fake_adapter = FakeAdapter([{"invalid": "not the expected format"}])

    monkeypatch.setattr("app.agents.tools.setting.get_adapter", lambda db=None: fake_adapter)

    result = json.loads(detect_conflicts(db_session, "p1", ["s1", "s2"]))
    assert len(result["conflicts"]) >= 1


def test_resolve_conflict_persists_in_agent_task(db_session):
    db_session.add(Project(id="p1", title="Test Project"))
    db_session.add(AgentTask(
        id="t1",
        project_id="p1",
        task_type="settings_mgr",
        status="running",
    ))
    db_session.commit()

    result = json.loads(resolve_conflict(db_session, "Gravity contradiction", "Use weak gravity everywhere", write_mode="apply"))
    assert result["status"] == "resolved"
    assert result["conflict_desc"] == "Gravity contradiction"
    assert result["resolution"] == "Use weak gravity everywhere"

    task = db_session.query(AgentTask).filter(AgentTask.id == "t1").first()
    resolved = task.task_metadata.get("resolved_conflicts", [])
    assert len(resolved) == 1
    assert resolved[0]["conflict_desc"] == "Gravity contradiction"
    assert resolved[0]["resolution"] == "Use weak gravity everywhere"
    assert "resolved_at" in resolved[0]


def test_resolve_conflict_no_active_task_fallback(db_session):
    db_session.add(Project(id="p1", title="Test Project"))
    db_session.commit()

    result = json.loads(resolve_conflict(db_session, "Key clash", "Merge settings"))
    assert result["status"] == "resolved"
    assert result["conflict_desc"] == "Key clash"
    assert result["resolution"] == "Merge settings"
