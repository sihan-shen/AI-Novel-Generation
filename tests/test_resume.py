import json
import logging

from app.agents.autonomy import AutonomyConfig
from app.agents.blackboard import Blackboard
from app.models.agent_task import AgentTask


def _make_snapshot_with_context():
    bb = Blackboard(
        project_id="p1",
        task={"type": "write_chapter", "chapter_outline_id": "o1", "target_words": 3000},
        autonomy_config=AutonomyConfig(),
    )
    bb.set_project_context(
        meta={"genre": "fantasy", "status": "active"},
        settings="Magic system details",
        outline="Volume 1 outline",
        style="Epic grand style",
    )
    bb.orchestrator_state = "WRITING"
    return bb.to_snapshot()


class TestRecoverAgentTasks:
    """Acceptance tests for _recover_agent_tasks resumable recovery."""

    def test_running_with_valid_snapshot_becomes_waiting_user(self, db_session, caplog):
        """(a) running + valid snapshot + non-terminal state → waiting_user (resumable)."""
        snapshot = _make_snapshot_with_context()
        task = AgentTask(
            id="task-a",
            project_id="p1",
            task_type="write_chapter",
            status="running",
            orchestrator_state="WRITING",
            blackboard_snapshot=json.dumps(snapshot, ensure_ascii=False),
        )
        db_session.add(task)
        db_session.commit()

        from app.main import _recover_agent_tasks
        _recover_agent_tasks()

        db_session.refresh(task)
        assert task.status == "waiting_user"
        assert task.orchestrator_state == "WRITING"

    def test_no_task_becomes_running_on_restart(self, db_session):
        """(b) NEGATIVE: no recovered task may end up in running status."""
        snapshot = _make_snapshot_with_context()
        for state in ["WRITING", "REVIEWING", "GATHERING_CONTEXT"]:
            task = AgentTask(
                id=f"task-{state}",
                project_id="p1",
                task_type="write_chapter",
                status="running",
                orchestrator_state=state,
                blackboard_snapshot=json.dumps(snapshot, ensure_ascii=False),
            )
            db_session.add(task)
        db_session.commit()

        from app.main import _recover_agent_tasks
        _recover_agent_tasks()

        running_tasks = db_session.query(AgentTask).filter(AgentTask.status == "running").all()
        assert len(running_tasks) == 0

    def test_done_state_plus_snapshot_becomes_failed(self, db_session):
        """(c) running + snapshot but terminal DONE state → failed."""
        snapshot = _make_snapshot_with_context()
        snapshot["orchestrator_state"] = "DONE"
        task = AgentTask(
            id="task-c",
            project_id="p1",
            task_type="write_chapter",
            status="running",
            orchestrator_state="DONE",
            blackboard_snapshot=json.dumps(snapshot, ensure_ascii=False),
        )
        db_session.add(task)
        db_session.commit()

        from app.main import _recover_agent_tasks
        _recover_agent_tasks()

        db_session.refresh(task)
        assert task.status == "failed"

    def test_invalid_snapshot_skips_row_and_logs_warning(self, db_session, caplog):
        """(d) invalid JSON snapshot → row skipped, caplog WARNING emitted."""
        caplog.set_level(logging.WARNING)
        task = AgentTask(
            id="task-d",
            project_id="p1",
            task_type="write_chapter",
            status="running",
            orchestrator_state="WRITING",
            blackboard_snapshot="{invalid json",
        )
        db_session.add(task)
        db_session.commit()

        from app.main import _recover_agent_tasks
        _recover_agent_tasks()

        db_session.refresh(task)
        assert task.status == "running"  # unchanged because skipped
        assert any("task-d" in rec.message for rec in caplog.records)

    def test_waiting_user_tasks_stay_waiting_user(self, db_session):
        """waiting_user tasks should remain waiting_user after recovery (not cancelled)."""
        snapshot = _make_snapshot_with_context()
        task = AgentTask(
            id="task-wu",
            project_id="p1",
            task_type="write_chapter",
            status="waiting_user",
            orchestrator_state="WAITING_USER",
            blackboard_snapshot=json.dumps(snapshot, ensure_ascii=False),
        )
        db_session.add(task)
        db_session.commit()

        from app.main import _recover_agent_tasks
        _recover_agent_tasks()

        db_session.refresh(task)
        assert task.status == "waiting_user"
        assert task.orchestrator_state == "WAITING_USER"


class TestBlackboardSnapshotRehydration:
    """Acceptance tests for blackboard snapshot round-trip with project context."""

    def test_snapshot_includes_project_context_fields(self):
        """(e) to_snapshot includes _project_meta/_settings_context/_outline_context/_style_context."""
        bb = Blackboard(
            project_id="p1",
            task={"type": "write_chapter", "chapter_outline_id": "o1", "target_words": 3000},
            autonomy_config=AutonomyConfig(),
        )
        bb.set_project_context(
            meta={"genre": "sci-fi"},
            settings="Space travel rules",
            outline="Galaxy map",
            style="Hard sci-fi",
        )
        snapshot = bb.to_snapshot()
        assert snapshot["_project_meta"] == {"genre": "sci-fi"}
        assert snapshot["_settings_context"] == "Space travel rules"
        assert snapshot["_outline_context"] == "Galaxy map"
        assert snapshot["_style_context"] == "Hard sci-fi"

    def test_from_snapshot_rehydrates_settings_context(self):
        """(f) from_snapshot rehydrates _settings_context non-empty."""
        bb = Blackboard(
            project_id="p1",
            task={"type": "write_chapter", "chapter_outline_id": "o1", "target_words": 3000},
            autonomy_config=AutonomyConfig(),
        )
        bb.set_project_context(
            meta={"genre": "horror"},
            settings="Dark magic rules",
            outline="Haunted house",
            style="Gothic",
        )
        snapshot = bb.to_snapshot()
        restored = Blackboard.from_snapshot(snapshot)
        assert restored._settings_context == "Dark magic rules"
        assert restored._outline_context == "Haunted house"
        assert restored._style_context == "Gothic"
        assert restored._project_meta == {"genre": "horror"}
