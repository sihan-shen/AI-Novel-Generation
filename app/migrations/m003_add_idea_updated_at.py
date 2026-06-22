"""Add updated_at column to ideas table.

Idempotent: checks if column exists before adding.
"""
from sqlalchemy import text

MIGRATION_KEY = "m003_add_idea_updated_at"


def run(engine):
    with engine.begin() as conn:
        columns = [row[1] for row in conn.execute(text(
            "PRAGMA table_info(ideas)"
        )).fetchall()]
        if "updated_at" in columns:
            return
        conn.execute(text(
            "ALTER TABLE ideas ADD COLUMN updated_at TIMESTAMP"
        ))
