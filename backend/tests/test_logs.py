"""Tests for device log endpoints."""
import pytest
from unittest.mock import patch, MagicMock

from app.models.device import Device


@pytest.fixture
def device(client, auth_headers, db_session):
    """Create a test device."""
    device = Device(
        device_id="log-test-device",
        api_key="test-api-key",
        customer_name="Test Co",
        location="Test Lab",
    )
    db_session.add(device)
    db_session.commit()
    return device


def create_mock_logs():
    """Create a set of mock log entries for testing."""
    return [
        {"level": "CRITICAL", "message": "Emergency stop triggered", "timestamp": "2025-06-05T14:30:00Z"},
        {"level": "ERROR", "message": "Sensor disconnected", "timestamp": "2025-06-05T14:25:00Z"},
        {"level": "WARNING", "message": "Throughput below threshold", "timestamp": "2025-06-05T14:20:00Z"},
        {"level": "INFO", "message": "State machine transitioned to idle", "timestamp": "2025-06-05T14:15:00Z"},
        {"level": "INFO", "message": "Cycle complete", "timestamp": "2025-06-05T14:10:00Z"},
        {"level": "DEBUG", "message": "Polling sensor A", "timestamp": "2025-06-05T14:05:00Z"},
    ]


# ─── Basic retrieval ──────────────────────────────────────────────────────────


@patch("app.routes.logs.metrics_db")
def test_list_logs_returns_all(mock_metrics_db, client, auth_headers, device):
    mock_logs = create_mock_logs()
    mock_metrics_db.get_logs.return_value = {
        "logs": mock_logs,
        "has_more": False,
        "next_before_timestamp": None,
    }

    resp = client.get("/api/devices/log-test-device/logs", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["logs"]) == 6
    assert data["device_id"] == "log-test-device"
    mock_metrics_db.get_logs.assert_called_once_with("log-test-device", None, 50, None)


@patch("app.routes.logs.metrics_db")
def test_list_logs_newest_first(mock_metrics_db, client, auth_headers, device):
    mock_logs = create_mock_logs()
    mock_metrics_db.get_logs.return_value = {
        "logs": mock_logs,
        "has_more": False,
        "next_before_timestamp": None,
    }

    resp = client.get("/api/devices/log-test-device/logs", headers=auth_headers)
    logs = resp.json()["logs"]
    assert logs[0]["level"] == "CRITICAL"
    assert logs[-1]["level"] == "DEBUG"


@patch("app.routes.logs.metrics_db")
def test_list_logs_response_shape(mock_metrics_db, client, auth_headers, device):
    mock_logs = create_mock_logs()
    mock_metrics_db.get_logs.return_value = {
        "logs": [mock_logs[0]],
        "has_more": False,
        "next_before_timestamp": None,
    }

    resp = client.get("/api/devices/log-test-device/logs", headers=auth_headers)
    log = resp.json()["logs"][0]
    assert "level" in log
    assert "message" in log
    assert "timestamp" in log


def test_list_logs_device_not_found(client, auth_headers):
    resp = client.get("/api/devices/nonexistent/logs", headers=auth_headers)
    assert resp.status_code == 404


def test_list_logs_requires_auth(client):
    resp = client.get("/api/devices/log-test-device/logs")
    assert resp.status_code == 401


# ─── Severity filtering ───────────────────────────────────────────────────────


@patch("app.routes.logs.metrics_db")
def test_filter_by_error(mock_metrics_db, client, auth_headers, device):
    mock_metrics_db.get_logs.return_value = {
        "logs": [
            {"level": "ERROR", "message": "Sensor disconnected", "timestamp": "2025-06-05T14:25:00Z"}
        ],
        "has_more": False,
        "next_before_timestamp": None,
    }

    resp = client.get("/api/devices/log-test-device/logs?level=ERROR", headers=auth_headers)
    assert resp.status_code == 200
    logs = resp.json()["logs"]
    assert len(logs) == 1
    assert logs[0]["level"] == "ERROR"
    mock_metrics_db.get_logs.assert_called_once_with("log-test-device", "ERROR", 50, None)


@patch("app.routes.logs.metrics_db")
def test_filter_by_info(mock_metrics_db, client, auth_headers, device):
    mock_metrics_db.get_logs.return_value = {
        "logs": [
            {"level": "INFO", "message": "State machine transitioned to idle", "timestamp": "2025-06-05T14:15:00Z"},
            {"level": "INFO", "message": "Cycle complete", "timestamp": "2025-06-05T14:10:00Z"},
        ],
        "has_more": False,
        "next_before_timestamp": None,
    }

    resp = client.get("/api/devices/log-test-device/logs?level=INFO", headers=auth_headers)
    logs = resp.json()["logs"]
    assert len(logs) == 2
    assert all(log["level"] == "INFO" for log in logs)


@patch("app.routes.logs.metrics_db")
def test_filter_by_warning(mock_metrics_db, client, auth_headers, device):
    mock_metrics_db.get_logs.return_value = {
        "logs": [
            {"level": "WARNING", "message": "Throughput below threshold", "timestamp": "2025-06-05T14:20:00Z"}
        ],
        "has_more": False,
        "next_before_timestamp": None,
    }

    resp = client.get("/api/devices/log-test-device/logs?level=WARNING", headers=auth_headers)
    logs = resp.json()["logs"]
    assert len(logs) == 1
    assert logs[0]["level"] == "WARNING"


@patch("app.routes.logs.metrics_db")
def test_filter_by_critical(mock_metrics_db, client, auth_headers, device):
    mock_metrics_db.get_logs.return_value = {
        "logs": [
            {"level": "CRITICAL", "message": "Emergency stop triggered", "timestamp": "2025-06-05T14:30:00Z"}
        ],
        "has_more": False,
        "next_before_timestamp": None,
    }

    resp = client.get("/api/devices/log-test-device/logs?level=CRITICAL", headers=auth_headers)
    logs = resp.json()["logs"]
    assert len(logs) == 1
    assert logs[0]["level"] == "CRITICAL"


@patch("app.routes.logs.metrics_db")
def test_filter_by_debug(mock_metrics_db, client, auth_headers, device):
    mock_metrics_db.get_logs.return_value = {
        "logs": [
            {"level": "DEBUG", "message": "Polling sensor A", "timestamp": "2025-06-05T14:05:00Z"}
        ],
        "has_more": False,
        "next_before_timestamp": None,
    }

    resp = client.get("/api/devices/log-test-device/logs?level=DEBUG", headers=auth_headers)
    logs = resp.json()["logs"]
    assert len(logs) == 1
    assert logs[0]["level"] == "DEBUG"


@patch("app.routes.logs.metrics_db")
def test_filter_level_case_insensitive(mock_metrics_db, client, auth_headers, device):
    mock_metrics_db.get_logs.return_value = {
        "logs": [
            {"level": "ERROR", "message": "Sensor disconnected", "timestamp": "2025-06-05T14:25:00Z"}
        ],
        "has_more": False,
        "next_before_timestamp": None,
    }

    resp = client.get("/api/devices/log-test-device/logs?level=error", headers=auth_headers)
    assert resp.status_code == 200
    logs = resp.json()["logs"]
    assert len(logs) == 1
    mock_metrics_db.get_logs.assert_called_once_with("log-test-device", "ERROR", 50, None)


def test_filter_invalid_level_returns_422(client, auth_headers, device):
    resp = client.get("/api/devices/log-test-device/logs?level=VERBOSE", headers=auth_headers)
    assert resp.status_code == 422


@patch("app.routes.logs.metrics_db")
def test_filter_no_matching_logs(mock_metrics_db, client, auth_headers, device):
    mock_metrics_db.get_logs.return_value = {
        "logs": [],
        "has_more": False,
        "next_before_timestamp": None,
    }

    resp = client.get("/api/devices/log-test-device/logs?level=DEBUG&before_timestamp=2025-06-05T14:00:00Z", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["logs"] == []


# ─── Pagination ───────────────────────────────────────────────────────────────


@patch("app.routes.logs.metrics_db")
def test_limit_parameter(mock_metrics_db, client, auth_headers, device):
    mock_logs = create_mock_logs()[:3]
    mock_metrics_db.get_logs.return_value = {
        "logs": mock_logs,
        "has_more": True,
        "next_before_timestamp": "2025-06-05T14:20:00Z",
    }

    resp = client.get("/api/devices/log-test-device/logs?limit=3", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["logs"]) == 3
    assert data["has_more"] is True
    assert data["next_before_timestamp"] is not None
    mock_metrics_db.get_logs.assert_called_once_with("log-test-device", None, 3, None)


@patch("app.routes.logs.metrics_db")
def test_has_more_false_when_fewer_than_limit(mock_metrics_db, client, auth_headers, device):
    mock_logs = create_mock_logs()
    mock_metrics_db.get_logs.return_value = {
        "logs": mock_logs,
        "has_more": False,
        "next_before_timestamp": None,
    }

    resp = client.get("/api/devices/log-test-device/logs?limit=100", headers=auth_headers)
    data = resp.json()
    assert data["has_more"] is False
    assert data["next_before_timestamp"] is None


@patch("app.routes.logs.metrics_db")
def test_cursor_pagination(mock_metrics_db, client, auth_headers, device):
    """Verify cursor pagination returns non-overlapping pages."""
    # First page: 3 logs
    page1_logs = create_mock_logs()[:3]
    mock_metrics_db.get_logs.side_effect = [
        {
            "logs": page1_logs,
            "has_more": True,
            "next_before_timestamp": page1_logs[-1]["timestamp"],
        },
        # Second page: 3 remaining logs
        {
            "logs": create_mock_logs()[3:6],
            "has_more": False,
            "next_before_timestamp": None,
        },
    ]

    # Fetch first page
    resp1 = client.get("/api/devices/log-test-device/logs?limit=3", headers=auth_headers)
    data1 = resp1.json()
    page1_messages = {log["message"] for log in data1["logs"]}
    assert len(page1_messages) == 3
    assert data1["has_more"] is True

    # Fetch second page with cursor
    cursor = data1["next_before_timestamp"]
    resp2 = client.get(f"/api/devices/log-test-device/logs?limit=3&before_timestamp={cursor}", headers=auth_headers)
    data2 = resp2.json()
    page2_messages = {log["message"] for log in data2["logs"]}

    # Verify no overlap
    assert page1_messages.isdisjoint(page2_messages), "Pagination returned duplicate logs"

    # Verify all 6 fixture logs are present
    all_messages = page1_messages | page2_messages
    fixture_messages = {
        "Polling sensor A", "Cycle complete", "State machine transitioned to idle",
        "Throughput below threshold", "Sensor disconnected", "Emergency stop triggered",
    }
    assert fixture_messages == all_messages
