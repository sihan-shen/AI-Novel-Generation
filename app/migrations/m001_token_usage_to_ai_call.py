"""Migrate rows from token_usage to ai_call.

Idempotent: checks for an existing marker row to avoid re-running.
"""
from sqlalchemy import text

MIGRATION_KEY = "m001_token_usage_to_ai_call"


def run(engine):
    with engine.begin() as conn:
        # Skip if token_usage no longer exists (already migrated or never existed)
        inspector_result = conn.execute(text(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='token_usage'"
        )).fetchone()
        if not inspector_result:
            return

        # Skip if migration already ran (check a sentinel row by id)
        already = conn.execute(text(
            "SELECT id FROM ai_call WHERE id = :k"
        ), {"k": MIGRATION_KEY}).fetchone()
        if already:
            return

        # Copy rows
        rows = conn.execute(text(
            "SELECT id, model, input_tokens, output_tokens, scenario, created_at FROM token_usage"
        )).fetchall()
        for r in rows:
            conn.execute(text(
                "INSERT INTO ai_call (id, project_id, scenario, model, prompt, response, "
                "input_tokens, output_tokens, duration_ms, status, error_message, created_at) "
                "VALUES (:id, NULL, :scenario, :model, '', '', :input_tokens, :output_tokens, "
                "NULL, 'success', NULL, :created_at)"
            ), {
                "id": r.id,
                "scenario": r.scenario or "",
                "model": r.model,
                "input_tokens": r.input_tokens or 0,
                "output_tokens": r.output_tokens or 0,
                "created_at": r.created_at,
            })

        # Insert sentinel row
        conn.execute(text(
            "INSERT INTO ai_call (id, scenario, model, status, input_tokens, output_tokens) "
            "VALUES (:k, '__migration__', '__migration__', 'success', 0, 0)"
        ), {"k": MIGRATION_KEY})
