"""Tests for the router-side confirm flow (Wave 2-T3 / todo 9)."""

import asyncio

import pytest

from app.models.project import Project
from app.routers.agent.shared import _confirm_outcomes, _pending_confirms


@pytest.fixture(autouse=True)
def _cleanup_confirms():
    """Ensure registries are clean before and after every test."""
    _pending_confirms.clear()
    _confirm_outcomes.clear()
    yield
    _pending_confirms.clear()
    _confirm_outcomes.clear()


def test_confirm_approve_sets_event_stores_outcome_and_cleans_up(client, db_session):
    """Given: a pending confirm event is registered.
    When: POST /chat/confirm with action=approve.
    Then: event is set, outcome stored, registry cleaned, 200 returned."""
    db_session.add(Project(id="p1", title="Test"))
    db_session.commit()

    event = asyncio.Event()
    _pending_confirms["cid"] = event
    assert not event.is_set()

    response = client.post(
        "/api/project/p1/agent/chat/confirm",
        json={"confirm_id": "cid", "action": "approve"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["data"]["status"] == "ok"
    assert "approve" in body["data"]["message"]
    assert event.is_set()
    assert _confirm_outcomes["cid"]["action"] == "approve"
    assert "cid" not in _pending_confirms


def test_confirm_reject_sets_event_and_stores_outcome(client, db_session):
    """Given: a pending confirm event is registered.
    When: POST /chat/confirm with action=reject.
    Then: event is set, outcome stored with reject action."""
    db_session.add(Project(id="p1", title="Test"))
    db_session.commit()

    event = asyncio.Event()
    _pending_confirms["cid_reject"] = event

    response = client.post(
        "/api/project/p1/agent/chat/confirm",
        json={"confirm_id": "cid_reject", "action": "reject"},
    )

    assert response.status_code == 200
    assert event.is_set()
    assert _confirm_outcomes["cid_reject"]["action"] == "reject"
    assert "cid_reject" not in _pending_confirms


def test_confirm_modify_sets_event_and_stores_modification(client, db_session):
    """Given: a pending confirm event is registered.
    When: POST /chat/confirm with action=modify and a modification string.
    Then: event is set, outcome stores both action and modification."""
    db_session.add(Project(id="p1", title="Test"))
    db_session.commit()

    event = asyncio.Event()
    _pending_confirms["cid_mod"] = event

    response = client.post(
        "/api/project/p1/agent/chat/confirm",
        json={"confirm_id": "cid_mod", "action": "modify", "modification": "changed args"},
    )

    assert response.status_code == 200
    assert event.is_set()
    assert _confirm_outcomes["cid_mod"]["action"] == "modify"
    assert _confirm_outcomes["cid_mod"]["modification"] == "changed args"
    assert "cid_mod" not in _pending_confirms


def test_confirm_unknown_id_returns_404(client, db_session):
    """Given: no pending confirm with the supplied id.
    When: POST /chat/confirm.
    Then: 404 with error status."""
    db_session.add(Project(id="p1", title="Test"))
    db_session.commit()

    response = client.post(
        "/api/project/p1/agent/chat/confirm",
        json={"confirm_id": "unknown", "action": "approve"},
    )

    assert response.status_code == 404
    body = response.json()
    assert body["status"] == "error"
    assert "Unknown" in body["message"]


def test_pending_actions_includes_confirm_ids(client, db_session):
    """Given: two pending confirm events are registered.
    When: GET /pending-actions.
    Then: response includes confirm_ids list with both ids."""
    db_session.add(Project(id="p1", title="Test"))
    db_session.commit()

    _pending_confirms["c1"] = asyncio.Event()
    _pending_confirms["c2"] = asyncio.Event()

    response = client.get("/api/project/p1/agent/pending-actions")

    assert response.status_code == 200
    body = response.json()
    assert "confirm_ids" in body["data"]
    assert sorted(body["data"]["confirm_ids"]) == ["c1", "c2"]
