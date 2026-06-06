"""Tests for the device metrics API endpoint."""
import pytest
from unittest.mock import patch
from app.models.device import Device


@pytest.fixture
def device(client, db_session):
    d = Device(device_id="metrics-device", api_key="mkey")
    db_session.add(d)
    db_session.commit()
    return d


MOCK_METRICS = {
    "throughput": [{"timestamp": "2025-06-05T12:00:00+00:00", "value": 1500.0, "metric_type": "throughput"}],
    "cycle_time": [{"timestamp": "2025-06-05T12:00:00+00:00", "value": 2.1, "metric_type": "cycle_time"}],
    "error_rate": [],
}


@patch("app.routes.metrics.metrics_db")
def test_get_metrics_returns_data(mock_db, client, auth_headers, device):
    mock_db.get_all_metrics.return_value = MOCK_METRICS
    mock_db.get_latest_metric.return_value = 1500.0

    resp = client.get("/api/devices/metrics-device/metrics", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["device_id"] == "metrics-device"
    assert "metrics" in data
    assert "latest" in data
    assert set(data["metrics"].keys()) == {"throughput", "cycle_time", "error_rate"}


@patch("app.routes.metrics.metrics_db")
def test_get_metrics_default_hours(mock_db, client, auth_headers, device):
    mock_db.get_all_metrics.return_value = MOCK_METRICS
    mock_db.get_latest_metric.return_value = None

    client.get("/api/devices/metrics-device/metrics", headers=auth_headers)
    mock_db.get_all_metrics.assert_called_once_with("metrics-device", 24)


@patch("app.routes.metrics.metrics_db")
def test_get_metrics_custom_hours(mock_db, client, auth_headers, device):
    mock_db.get_all_metrics.return_value = MOCK_METRICS
    mock_db.get_latest_metric.return_value = None

    client.get("/api/devices/metrics-device/metrics?hours=48", headers=auth_headers)
    mock_db.get_all_metrics.assert_called_once_with("metrics-device", 48)


@patch("app.routes.metrics.metrics_db")
def test_get_metrics_latest_values(mock_db, client, auth_headers, device):
    mock_db.get_all_metrics.return_value = MOCK_METRICS
    mock_db.get_latest_metric.side_effect = [1500.0, 2.1, 0.01]

    resp = client.get("/api/devices/metrics-device/metrics", headers=auth_headers)
    latest = resp.json()["latest"]
    assert latest["throughput"] == 1500.0
    assert latest["cycle_time"] == 2.1
    assert latest["error_rate"] == 0.01


def test_get_metrics_device_not_found(client, auth_headers):
    resp = client.get("/api/devices/nonexistent/metrics", headers=auth_headers)
    assert resp.status_code == 404


def test_get_metrics_requires_auth(client, device):
    resp = client.get("/api/devices/metrics-device/metrics")
    assert resp.status_code == 401


def test_get_metrics_hours_out_of_range(client, auth_headers, device):
    resp = client.get("/api/devices/metrics-device/metrics?hours=0", headers=auth_headers)
    assert resp.status_code == 422

    resp = client.get("/api/devices/metrics-device/metrics?hours=721", headers=auth_headers)
    assert resp.status_code == 422
