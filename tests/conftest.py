from collections.abc import Generator
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.core.config import settings
from app.db.database import Base, get_db
from main import app


@pytest.fixture
def engine(tmp_path):
    """Create a test database engine."""
    engine = create_engine(
        f"sqlite:///{tmp_path / 'test.db'}",
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(bind=engine)
    return engine


@pytest.fixture
def db(engine) -> Generator[Session, None, None]:
    """Create a test database session."""
    testing_session = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    db_session = testing_session()
    try:
        yield db_session
    finally:
        db_session.close()


@pytest.fixture
def client(db: Session) -> Generator[TestClient, None, None]:
    """Create a test client with overridden database."""
    def override_get_db() -> Generator[Session, None, None]:
        yield db

    previous_scheduler_enabled = settings.scheduler_enabled
    settings.scheduler_enabled = False
    app.dependency_overrides[get_db] = override_get_db
    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        settings.scheduler_enabled = previous_scheduler_enabled
        app.dependency_overrides.clear()
