"""Add metadata and updated_at columns to agent_tasks.

Idempotent: checks if columns exist before adding.
"""
from sqlalchemy import text


MIGRATION_KEY = "m002_add_agent_task_columns"


def run(engine):
    with engine.begin() as conn:
        # Check if already migrated by looking for the metadata column
        columns = [row[1] for row in conn.execute(text(
            "PRAGMA table_info(agent_tasks)"
        )).fetchall()]
        if "metadata" in columns and "updated_at" in columns:
            return

        # Add columns one at a time (SQLite limitation)
        if "metadata" not in columns:
            conn.execute(text(
                "ALTER TABLE agent_tasks ADD COLUMN metadata TEXT DEFAULT '{}'"
            ))
        if "updated_at" not in columns:
            conn.execute(text(
                "ALTER TABLE agent_tasks ADD COLUMN updated_at TIMESTAMP"
            ))
