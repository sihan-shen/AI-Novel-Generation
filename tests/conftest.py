import os

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

os.environ["DATABASE_URL"] = "sqlite:///:memory:"  # must run before any app.* import

from app import database as app_database  # noqa: E402
from app.database import Base, get_db  # noqa: E402
from app.main import app  # noqa: E402


@pytest.fixture
def db_session():
    """Per-test in-memory SQLite, shared with the FastAPI app so route handlers
    see the same rows tests insert directly.

    StaticPool is required: with the default pool, each new connection to
    sqlite:///:memory: opens its own private database, so writes in the test
    session would be invisible to route handlers that fetch a different
    connection from the pool.
    """
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    original_engine = app_database.engine
    original_session_local = app_database.SessionLocal
    app_database.engine = engine
    app_database.SessionLocal = TestingSessionLocal

    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)
        engine.dispose()
        app_database.engine = original_engine
        app_database.SessionLocal = original_session_local


@pytest.fixture
def client(db_session):
    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
