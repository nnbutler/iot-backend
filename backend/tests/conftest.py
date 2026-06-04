from typing import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base, get_db
from app.main import app

# Use the postgres service (accessible inside docker-compose)
TEST_DATABASE_URL = "postgresql+psycopg://postgres:postgres@postgres:5432/device_manager"


@pytest.fixture(scope="session")
def db_engine():
    """Create test database engine."""
    engine = create_engine(TEST_DATABASE_URL)
    Base.metadata.create_all(bind=engine)
    yield engine
    # Note: We don't drop tables after tests to preserve state for debugging


@pytest.fixture(scope="function")
def db_session(db_engine) -> Generator:
    """Provide a test database session."""
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=db_engine)
    session = SessionLocal()
    yield session
    session.rollback()
    session.close()


@pytest.fixture(scope="function")
def client(db_session) -> Generator:
    """Provide a FastAPI test client."""

    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
