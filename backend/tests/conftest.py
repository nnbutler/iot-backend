from typing import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from app.database import Base, get_db
from app.main import app
from app.utils.security import create_access_token

TEST_DATABASE_URL = "postgresql+psycopg://postgres:postgres@postgres:5432/device_manager"


@pytest.fixture(scope="session")
def db_engine():
    engine = create_engine(TEST_DATABASE_URL)
    Base.metadata.create_all(bind=engine)
    yield engine
    engine.dispose()


@pytest.fixture(scope="session", autouse=True)
def reset_db_state(db_engine):
    """
    Reset all mutable state once before the test session starts.
    Removes any data created by smoke tests / previous runs, while preserving
    the seeded error_types and repair_actions. User-added repair_actions are
    identified by having a non-NULL created_by.
    """
    with db_engine.connect() as conn:
        with conn.begin():
            conn.execute(text("DELETE FROM repair_outcomes"))
            conn.execute(text("DELETE FROM device_error_history"))
            conn.execute(text("DELETE FROM device_logs"))
            conn.execute(text("DELETE FROM mqtt_credentials"))
            conn.execute(text("DELETE FROM commands"))
            conn.execute(text("DELETE FROM devices"))
            # Remove any repair actions added via the API (seeded ones have NULL created_by)
            conn.execute(text("DELETE FROM repair_actions WHERE created_by IS NOT NULL"))
            # Reset success stats on seeded actions back to defaults
            conn.execute(text(
                "UPDATE repair_actions SET success_rate = 0.5, occurrences = 0, successful_occurrences = 0"
            ))


@pytest.fixture(scope="function")
def db_session(db_engine):
    """
    Each test runs inside an outer transaction that is rolled back at teardown.
    Route handlers call session.commit(), which with join_transaction_mode="create_savepoint"
    releases/re-issues SAVEPOINTs rather than actually committing to the DB.
    The outer rollback undoes everything, giving true per-test isolation.
    """
    connection = db_engine.connect()
    transaction = connection.begin()
    session = Session(bind=connection, join_transaction_mode="create_savepoint")
    yield session
    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture(scope="function")
def client(db_session) -> Generator:
    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def auth_headers() -> dict:
    """JWT Authorization headers for a 'support' dashboard user."""
    return {"Authorization": f"Bearer {create_access_token('support')}"}


@pytest.fixture
def other_user_headers() -> dict:
    """JWT Authorization headers for a different user (for recorded_by assertions)."""
    return {"Authorization": f"Bearer {create_access_token('alice')}"}


@pytest.fixture
def registered_device(client) -> tuple[str, str]:
    """Register a device and return (device_id, plaintext_api_key)."""
    resp = client.post("/api/devices/register", json={
        "device_id": "plc-fixture",
        "device_type": "plc",
        "location": "Test Lab, TX",
        "customer_name": "Fixture Co",
        "firmware_version": "2.0.0",
    })
    assert resp.status_code == 201
    data = resp.json()
    return data["device_id"], data["api_key"]


@pytest.fixture
def device_api_headers(registered_device) -> tuple[str, dict]:
    """Return (device_id, api_key_headers) for a registered device."""
    device_id, api_key = registered_device
    return device_id, {"Authorization": f"Bearer {api_key}"}
