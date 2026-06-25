from contextlib import contextmanager

from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.config import settings

engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False, "timeout": 30},
    pool_pre_ping=True,
    echo=False,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


@event.listens_for(engine, "connect")
def _set_sqlite_pragmas(dbapi_conn, connection_record):
    cursor = dbapi_conn.cursor()
    cursor.execute("PRAGMA journal_mode=WAL;")
    cursor.execute("PRAGMA busy_timeout=30000;")
    cursor.close()


def init_db():
    """Import all models so Base has them registered, then create tables."""
    from app.models import project, outline, setting, chapter, style, review, idea, ai_call, agent_task, agent_message, chapter_snapshot  # noqa
    Base.metadata.create_all(bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def get_db_context():
    """Context manager that yields a DB session and closes it on exit.

    Use for non-request-scoped DB access (lifespan events, background tasks)
    where FastAPI's dependency injection is not available.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
