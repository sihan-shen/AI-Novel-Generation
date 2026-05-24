from datetime import datetime
from app.models.ai_call import AICall


def test_ai_call_insert_with_minimum_fields(db_session):
    call = AICall(
        scenario="writing",
        model="claude-sonnet-4-6",
        input_tokens=100,
        output_tokens=50,
        status="success",
    )
    db_session.add(call)
    db_session.commit()
    db_session.refresh(call)
    assert call.id is not None
    assert call.scenario == "writing"
    assert call.input_tokens == 100
    assert call.output_tokens == 50
    assert call.status == "success"
    assert isinstance(call.created_at, datetime)


def test_ai_call_with_prompt_response_and_duration(db_session):
    call = AICall(
        scenario="outline_gen",
        model="claude-sonnet-4-6",
        prompt="Write a chapter outline",
        response="Chapter 1: ...",
        input_tokens=200,
        output_tokens=300,
        duration_ms=4500,
        status="success",
        project_id="proj-123",
    )
    db_session.add(call)
    db_session.commit()
    db_session.refresh(call)
    assert call.prompt == "Write a chapter outline"
    assert call.duration_ms == 4500
    assert call.project_id == "proj-123"


def test_ai_call_error_status(db_session):
    call = AICall(
        scenario="review",
        model="gpt-4-turbo",
        status="error",
        error_message="rate limit",
        input_tokens=0,
        output_tokens=0,
    )
    db_session.add(call)
    db_session.commit()
    db_session.refresh(call)
    assert call.status == "error"
    assert call.error_message == "rate limit"


from sqlalchemy import text
from app.migrations import m001_token_usage_to_ai_call


# Production has a legacy `token_usage` table; this snippet mirrors its
# schema so the migration tests can simulate a fresh-from-prod snapshot
# without relying on the (now-removed) Python TokenUsage model.
_LEGACY_TOKEN_USAGE_DDL = """
CREATE TABLE IF NOT EXISTS token_usage (
    id TEXT PRIMARY KEY,
    model TEXT NOT NULL,
    input_tokens INTEGER DEFAULT 0,
    output_tokens INTEGER DEFAULT 0,
    scenario TEXT DEFAULT '',
    created_at TIMESTAMP
)
"""


def test_migration_copies_token_usage_rows(db_session):
    engine = db_session.get_bind()
    with engine.begin() as conn:
        conn.execute(text(_LEGACY_TOKEN_USAGE_DDL))
        conn.execute(text(
            "INSERT INTO token_usage (id, model, input_tokens, output_tokens, scenario, created_at) "
            "VALUES ('t1', 'claude', 100, 50, 'writing', '2026-05-17 10:00:00')"
        ))

    m001_token_usage_to_ai_call.run(engine)

    with engine.connect() as conn:
        row = conn.execute(text("SELECT * FROM ai_call WHERE id='t1'")).fetchone()
        assert row is not None
        assert row.model == "claude"
        assert row.input_tokens == 100
        assert row.scenario == "writing"


def test_migration_is_idempotent(db_session):
    engine = db_session.get_bind()
    with engine.begin() as conn:
        conn.execute(text(_LEGACY_TOKEN_USAGE_DDL))
        conn.execute(text(
            "INSERT INTO token_usage (id, model, input_tokens, output_tokens, scenario, created_at) "
            "VALUES ('t2', 'gpt', 100, 50, 'review', '2026-05-17 10:00:00')"
        ))

    m001_token_usage_to_ai_call.run(engine)
    m001_token_usage_to_ai_call.run(engine)  # second call should be a no-op

    with engine.connect() as conn:
        rows = conn.execute(text("SELECT * FROM ai_call WHERE id='t2'")).fetchall()
        assert len(rows) == 1


def test_migration_skips_when_table_absent(db_session):
    """Fresh installs have no token_usage table; migration must no-op."""
    engine = db_session.get_bind()
    # No CREATE TABLE — token_usage simply doesn't exist
    m001_token_usage_to_ai_call.run(engine)  # should not raise

    with engine.connect() as conn:
        count = conn.execute(text("SELECT COUNT(*) FROM ai_call")).scalar()
        assert count == 0
