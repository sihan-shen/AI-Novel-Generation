"""SSE end-to-end tests — parse full event sequence, headers, brainstorm flow, reconnect."""

import json

import pytest

import app.routers.agent as agent_module


class FakeAdapter:
    """Mock LLM adapter that returns predetermined JSON responses."""

    async def generate(self, messages, **kwargs):
        from app.llm.adapter import LLMResponse

        prompt = messages[-1]["content"] if messages else ""
        # Intent detection prompt used by _detect_intent
        if "判断意图" in prompt:
            return LLMResponse(
                content=json.dumps({"intent": "writing"}),
                usage={"input_tokens": 10, "output_tokens": 5},
            )
        # Normal agent loop — finish immediately so the orchestrator runs through quickly
        return LLMResponse(
            content=json.dumps({"action": "finish", "summary": "done"}),
            usage={"input_tokens": 10, "output_tokens": 5},
        )

    def count_tokens(self, text: str) -> int:
        return 10


def _patch_agent_module(db_session):
    """Monkeypatch agent router to use test DB and FakeAdapter."""
    original_get_adapter = agent_module.get_adapter
    original_session_local = agent_module.SessionLocal

    def patched_get_adapter(db=None):
        return FakeAdapter()

    agent_module.get_adapter = patched_get_adapter
    from app import database as app_database

    agent_module.SessionLocal = app_database.SessionLocal
    return original_get_adapter, original_session_local


def _restore_agent_module(original_get_adapter, original_session_local):
    agent_module.get_adapter = original_get_adapter
    agent_module.SessionLocal = original_session_local


def _parse_sse_events(text: str) -> list[dict]:
    """Parse SSE text into list of {event, data} dicts."""
    events = []
    for block in text.strip().split("\n\n"):
        if not block.strip():
            continue
        event = None
        data = None
        for line in block.strip().split("\n"):
            if line.startswith("event: "):
                event = line[len("event: "):]
            elif line.startswith("data: "):
                data = line[len("data: "):]
        if event is not None:
            events.append({"event": event, "data": json.loads(data) if data else None})
    return events


def test_sse_full_event_sequence(client, db_session):
    """Given: a project exists. When: POST to chat/stream.
    Then: the SSE event sequence contains agent_start before done."""
    from app.models.project import Project

    db_session.add(Project(id="p1", title="Test Project"))
    db_session.commit()

    orig_adapter, orig_session = _patch_agent_module(db_session)
    try:
        with client.stream(
            "POST",
            "/api/project/p1/agent/chat/stream",
            json={"message": "Write chapter 1", "chapter_outline_id": "o1", "target_words": 100},
        ) as response:
            assert response.status_code == 200
            content = ""
            for chunk in response.iter_text():
                content += chunk
                if "event: done\n" in content:
                    break

            events = _parse_sse_events(content)
            event_types = [e["event"] for e in events]

            assert "agent_start" in event_types, (
                f"Expected agent_start in events, got: {event_types}"
            )
            assert "done" in event_types, (
                f"Expected done in events, got: {event_types}"
            )
            assert event_types.index("agent_start") < event_types.index("done"), (
                f"agent_start should come before done in: {event_types}"
            )
    finally:
        _restore_agent_module(orig_adapter, orig_session)


def test_sse_headers_correct(client, db_session):
    """Given: a project exists. When: POST to chat/stream.
    Then: response headers include SSE-specific cache and buffering directives."""
    from app.models.project import Project

    db_session.add(Project(id="p1", title="Test Project"))
    db_session.commit()

    orig_adapter, orig_session = _patch_agent_module(db_session)
    try:
        with client.stream(
            "POST",
            "/api/project/p1/agent/chat/stream",
            json={"message": "Write chapter 1", "chapter_outline_id": "o1", "target_words": 100},
        ) as response:
            assert response.status_code == 200
            # Consume at least one chunk so headers are fully materialised
            for chunk in response.iter_text():
                if "event:" in chunk:
                    break

            assert response.headers.get("Cache-Control") == "no-cache"
            assert response.headers.get("Connection") == "keep-alive"
            assert response.headers.get("X-Accel-Buffering") == "no"
    finally:
        _restore_agent_module(orig_adapter, orig_session)


def test_sse_brainstorm_flow_events(client, db_session):
    """Given: a project exists. When: POST with /brainstorm command.
    Then: brainstorm events are emitted."""
    from app.models.project import Project

    db_session.add(Project(id="p1", title="Test Project"))
    db_session.commit()

    orig_adapter, orig_session = _patch_agent_module(db_session)
    try:
        with client.stream(
            "POST",
            "/api/project/p1/agent/chat/stream",
            json={"message": "/brainstorm Give me ideas"},
        ) as response:
            assert response.status_code == 200
            content = ""
            for chunk in response.iter_text():
                content += chunk
                if "brainstorm_response" in content or "event: done\n" in content:
                    break

            events = _parse_sse_events(content)
            event_types = [e["event"] for e in events]

            has_brainstorm_start = any(
                e["event"] == "agent_start" and e["data"].get("agent") == "brainstorm"
                for e in events
            )
            has_brainstorm_response = "brainstorm_response" in event_types
            assert has_brainstorm_start or has_brainstorm_response, (
                f"Expected brainstorm events, got: {event_types}"
            )
    finally:
        _restore_agent_module(orig_adapter, orig_session)


def test_sse_reconnect_with_no_active_task(client, db_session):
    """Given: no active task. When: POST with resume_from=5.
    Then: reconnect event with no_active_task is emitted."""
    from app.models.project import Project

    db_session.add(Project(id="p1", title="Test Project"))
    db_session.commit()

    # Resume path does not invoke the orchestrator — no adapter/session patch needed
    with client.stream(
        "POST",
        "/api/project/p1/agent/chat/stream?resume_from=5",
        json={"message": "test", "chapter_outline_id": "x", "target_words": 10},
    ) as response:
        assert response.status_code == 200
        content = ""
        for chunk in response.iter_text():
            content += chunk
            if "reconnect" in content:
                break

        events = _parse_sse_events(content)
        reconnect_events = [e for e in events if e["event"] == "reconnect"]
        assert len(reconnect_events) == 1
        assert reconnect_events[0]["data"].get("status") == "no_active_task"


@pytest.mark.skip(reason="100-turn limit is covered by unit test in test_agent_router.py")
def test_sse_brainstorm_100_turn_end():
    """Skipped: turn limit logic is tested at unit level; e2e would require 100 turns."""
    pass
