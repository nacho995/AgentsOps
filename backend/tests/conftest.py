"""Shared pytest fixtures.

Every test runs against a throwaway in-memory SQLite database so the suite is
hermetic and leaves ``agentops.db`` untouched. ``StaticPool`` keeps the single
in-memory connection alive for the whole test (a fresh connection would see an
empty schema), and the ``get_db`` dependency is overridden to hand out sessions
bound to that engine.
"""

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.database import Base, get_db
from app.main import app


@pytest.fixture
def client() -> Iterator[TestClient]:
    """Yield a TestClient wired to an isolated in-memory database."""

    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(
        bind=engine,
        autoflush=False,
        autocommit=False,
    )
    Base.metadata.create_all(bind=engine)

    def override_get_db() -> Iterator:
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


@pytest.fixture
def db_session() -> Iterator[Session]:
    """Yield a session bound to an isolated in-memory database (no HTTP)."""

    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    session = sessionmaker(bind=engine)()

    yield session

    session.close()
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


def build_execution_payload(**overrides) -> dict:
    """Return a valid create-execution payload, tweakable via keyword args."""

    payload = {
        "agent_name": "recon-agent",
        "model": "claude-opus-5",
        "priority": "high",
        "task_type": "security_analysis",
        "input_text": "Scan the target scope for exposed services.",
    }
    payload.update(overrides)
    return payload
