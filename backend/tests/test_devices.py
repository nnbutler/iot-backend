"""Tests for device registration, status, and heartbeat endpoints."""
import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import Mock
from app.models.device import Device, DeviceErrorHistory


# ─── GET /api/devices ─────────────────────────────────────────────────────────


def test_list_devices_returns_empty_list(client, auth_headers):
    resp = client.get("/api/devices", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json() == {"devices": []}


def test_list_devices_requires_auth(client):
    assert client.get("/api/devices").status_code == 401


def test_list_devices_rejects_bad_token(client):
    resp = client.get("/api/devices", headers={"Authorization": "Bearer not-a-token"})
    assert resp.status_code == 401


def test_list_devices_shows_registered_device(client, auth_headers):
    client.post("/api/devices/register", json={"device_id": "plc-list-01"})
    resp = client.get("/api/devices", headers=auth_headers)
    assert resp.status_code == 200
    ids = [d["device_id"] for d in resp.json()["devices"]]
    assert "plc-list-01" in ids


def test_list_devices_response_shape(client, auth_headers):
    client.post("/api/devices/register", json={
        "device_id": "plc-shape",
        "customer_name": "Acme Inc",
        "location": "Phoenix, AZ",
    })
    devices = client.get("/api/devices", headers=auth_headers).json()["devices"]
    d = next(d for d in devices if d["device_id"] == "plc-shape")
    assert d["customer_name"] == "Acme Inc"
    assert d["location"] == "Phoenix, AZ"
    assert d["online"] is False
    assert d["last_error"] is None
    assert "uptime_percent" in d
    assert "last_seen" in d


def test_list_devices_sorted_by_device_id(client, auth_headers):
    for name in ["plc-zzz", "plc-aaa", "plc-mmm"]:
        client.post("/api/devices/register", json={"device_id": name})
    devices = client.get("/api/devices", headers=auth_headers).json()["devices"]
    ids = [d["device_id"] for d in devices]
    assert ids == sorted(ids)


# ─── POST /api/devices/register ───────────────────────────────────────────────


def test_register_device_success(client):
    resp = client.post("/api/devices/register", json={"device_id": "plc-new"})
    assert resp.status_code == 201
    data = resp.json()
    assert data["device_id"] == "plc-new"
    assert "api_key" in data
    assert len(data["api_key"]) > 20


def test_register_device_stores_all_fields(client, auth_headers):
    client.post("/api/devices/register", json={
        "device_id": "plc-fields",
        "device_type": "plc",
        "location": "Denver, CO",
        "customer_name": "Beta Corp",
        "firmware_version": "3.1.4",
    })
    status = client.get("/api/devices/plc-fields/status", headers=auth_headers).json()
    assert status["device_type"] == "plc"
    assert status["location"] == "Denver, CO"
    assert status["customer_name"] == "Beta Corp"
    assert status["firmware_version"] == "3.1.4"


def test_register_device_duplicate_returns_409(client):
    from unittest.mock import patch
    client.post("/api/devices/register", json={"device_id": "plc-dup"})
    with patch("app.config.settings") as mock_settings:
        mock_settings.DEBUG = False
        resp = client.post("/api/devices/register", json={"device_id": "plc-dup"})
    assert resp.status_code == 409
    assert "already registered" in resp.json()["detail"]


def test_register_device_each_gets_unique_api_key(client):
    r1 = client.post("/api/devices/register", json={"device_id": "plc-key-a"}).json()
    r2 = client.post("/api/devices/register", json={"device_id": "plc-key-b"}).json()
    assert r1["api_key"] != r2["api_key"]


def test_register_device_minimal_payload(client):
    resp = client.post("/api/devices/register", json={"device_id": "plc-minimal"})
    assert resp.status_code == 201


def test_register_device_missing_device_id_returns_422(client):
    resp = client.post("/api/devices/register", json={"location": "Nowhere"})
    assert resp.status_code == 422


# ─── GET /api/devices/{device_id}/status ──────────────────────────────────────


def test_device_status_requires_auth(client, registered_device):
    device_id, _ = registered_device
    assert client.get(f"/api/devices/{device_id}/status").status_code == 401


def test_device_status_not_found(client, auth_headers):
    assert client.get("/api/devices/does-not-exist/status", headers=auth_headers).status_code == 404


def test_device_status_no_error(client, auth_headers):
    client.post("/api/devices/register", json={"device_id": "plc-no-err"})
    resp = client.get("/api/devices/plc-no-err/status", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["device_id"] == "plc-no-err"
    assert data["online"] is False
    assert data["last_error"] is None
    assert data["troubleshooting"] is None


def test_device_status_response_shape(client, auth_headers, registered_device):
    device_id, _ = registered_device
    resp = client.get(f"/api/devices/{device_id}/status", headers=auth_headers)
    data = resp.json()
    for field in ("device_id", "online", "last_seen", "state", "firmware_version",
                  "location", "customer_name", "device_type", "last_error", "troubleshooting"):
        assert field in data, f"missing field: {field}"


def test_device_status_with_known_error_shows_troubleshooting(client, auth_headers, device_api_headers):
    device_id, api_headers = device_api_headers
    client.patch(f"/api/devices/{device_id}/heartbeat", json={
        "online": True,
        "last_error": "sensor_disconnected",
        "last_error_message": "Sensor gone dark",
    }, headers=api_headers)
    resp = client.get(f"/api/devices/{device_id}/status", headers=auth_headers)
    data = resp.json()
    assert data["last_error"]["code"] == "sensor_disconnected"
    assert data["last_error"]["message"] == "Sensor gone dark"
    assert data["last_error"]["occurred_at"] is not None
    assert data["troubleshooting"]["display_name"] == "Sensor Disconnected"
    assert len(data["troubleshooting"]["repair_actions"]) == 3


def test_device_status_with_unknown_error_has_no_troubleshooting(client, auth_headers, device_api_headers):
    device_id, api_headers = device_api_headers
    client.patch(f"/api/devices/{device_id}/heartbeat", json={
        "online": True,
        "last_error": "totally_unknown_error_xyz",
    }, headers=api_headers)
    resp = client.get(f"/api/devices/{device_id}/status", headers=auth_headers)
    data = resp.json()
    assert data["last_error"]["code"] == "totally_unknown_error_xyz"
    assert data["troubleshooting"] is None


def test_device_status_troubleshooting_repair_actions_ordered_by_step(client, auth_headers, device_api_headers):
    device_id, api_headers = device_api_headers
    client.patch(f"/api/devices/{device_id}/heartbeat", json={
        "online": True,
        "last_error": "photoeye_misaligned",
    }, headers=api_headers)
    actions = client.get(f"/api/devices/{device_id}/status", headers=auth_headers).json()[
        "troubleshooting"]["repair_actions"]
    steps = [a["step"] for a in actions]
    assert steps == sorted(steps)


# ─── PATCH /api/devices/{device_id}/heartbeat ─────────────────────────────────


def test_heartbeat_requires_valid_api_key(client, registered_device):
    device_id, _ = registered_device
    resp = client.patch(f"/api/devices/{device_id}/heartbeat",
                        json={"online": True},
                        headers={"Authorization": "Bearer wrong-key"})
    assert resp.status_code == 401


def test_heartbeat_requires_auth_header(client, registered_device):
    device_id, _ = registered_device
    assert client.patch(f"/api/devices/{device_id}/heartbeat", json={"online": True}).status_code == 401


def test_heartbeat_updates_online_status(client, auth_headers, device_api_headers):
    device_id, api_headers = device_api_headers
    resp = client.patch(f"/api/devices/{device_id}/heartbeat",
                        json={"online": True}, headers=api_headers)
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"
    status = client.get(f"/api/devices/{device_id}/status", headers=auth_headers).json()
    assert status["online"] is True
    assert status["last_seen"] is not None


def test_heartbeat_updates_state(client, auth_headers, device_api_headers):
    device_id, api_headers = device_api_headers
    client.patch(f"/api/devices/{device_id}/heartbeat",
                 json={"online": True, "state": "running"}, headers=api_headers)
    status = client.get(f"/api/devices/{device_id}/status", headers=auth_headers).json()
    assert status["state"] == "running"


def test_heartbeat_updates_firmware_version(client, auth_headers, device_api_headers):
    device_id, api_headers = device_api_headers
    client.patch(f"/api/devices/{device_id}/heartbeat",
                 json={"online": True, "firmware_version": "9.9.9"}, headers=api_headers)
    status = client.get(f"/api/devices/{device_id}/status", headers=auth_headers).json()
    assert status["firmware_version"] == "9.9.9"


def test_heartbeat_sets_error_opens_history(client, auth_headers, db_session, device_api_headers):
    from app.models.device import DeviceErrorHistory
    device_id, api_headers = device_api_headers
    client.patch(f"/api/devices/{device_id}/heartbeat", json={
        "online": True,
        "last_error": "sensor_disconnected",
        "last_error_message": "Sensor X offline",
    }, headers=api_headers)

    db_session.expire_all()
    entry = db_session.query(DeviceErrorHistory).filter(
        DeviceErrorHistory.device_id == device_id,
        DeviceErrorHistory.resolved_at.is_(None),
    ).first()
    assert entry is not None
    assert entry.error_message == "Sensor X offline"


def test_heartbeat_clears_error_closes_history(client, auth_headers, db_session, device_api_headers):
    from app.models.device import DeviceErrorHistory
    device_id, api_headers = device_api_headers
    # Set error
    client.patch(f"/api/devices/{device_id}/heartbeat",
                 json={"online": True, "last_error": "internet_down"}, headers=api_headers)
    # Clear error
    client.patch(f"/api/devices/{device_id}/heartbeat",
                 json={"online": True, "last_error": None}, headers=api_headers)

    db_session.expire_all()
    open_errors = db_session.query(DeviceErrorHistory).filter(
        DeviceErrorHistory.device_id == device_id,
        DeviceErrorHistory.resolved_at.is_(None),
    ).all()
    assert len(open_errors) == 0

    resolved = db_session.query(DeviceErrorHistory).filter(
        DeviceErrorHistory.device_id == device_id,
    ).first()
    assert resolved.resolved_at is not None


def test_heartbeat_error_change_closes_old_and_opens_new(client, db_session, device_api_headers):
    from app.models.device import DeviceErrorHistory
    device_id, api_headers = device_api_headers
    client.patch(f"/api/devices/{device_id}/heartbeat",
                 json={"online": True, "last_error": "internet_down"}, headers=api_headers)
    client.patch(f"/api/devices/{device_id}/heartbeat",
                 json={"online": True, "last_error": "sensor_disconnected"}, headers=api_headers)

    db_session.expire_all()
    all_errors = db_session.query(DeviceErrorHistory).filter(
        DeviceErrorHistory.device_id == device_id
    ).all()
    assert len(all_errors) == 2
    resolved = [e for e in all_errors if e.resolved_at is not None]
    open_errors = [e for e in all_errors if e.resolved_at is None]
    assert len(resolved) == 1
    assert len(open_errors) == 1
    assert open_errors[0].error_message == "sensor_disconnected"


def test_heartbeat_same_error_no_duplicate_history(client, db_session, device_api_headers):
    from app.models.device import DeviceErrorHistory
    device_id, api_headers = device_api_headers
    # Send same error twice
    for _ in range(3):
        client.patch(f"/api/devices/{device_id}/heartbeat",
                     json={"online": True, "last_error": "sensor_disconnected"}, headers=api_headers)

    db_session.expire_all()
    entries = db_session.query(DeviceErrorHistory).filter(
        DeviceErrorHistory.device_id == device_id
    ).all()
    assert len(entries) == 1


def test_heartbeat_uptime_starts_at_100(client, auth_headers, device_api_headers):
    device_id, api_headers = device_api_headers
    client.patch(f"/api/devices/{device_id}/heartbeat",
                 json={"online": True}, headers=api_headers)
    devices = client.get("/api/devices", headers=auth_headers).json()["devices"]
    device = next(d for d in devices if d["device_id"] == device_id)
    assert device["uptime_percent"] == 100.0


# ── _as_utc helper ────────────────────────────────────────────────────────────

def test_as_utc_returns_none_for_none():
    from app.routes.devices import _as_utc
    assert _as_utc(None) is None


def test_as_utc_adds_utc_to_naive():
    from app.routes.devices import _as_utc
    naive = datetime(2025, 6, 5, 12, 0, 0)
    result = _as_utc(naive)
    assert result.tzinfo is not None
    assert result == datetime(2025, 6, 5, 12, 0, 0, tzinfo=timezone.utc)


def test_as_utc_preserves_aware():
    from app.routes.devices import _as_utc
    aware = datetime(2025, 6, 5, 12, 0, 0, tzinfo=timezone.utc)
    assert _as_utc(aware) is aware


# ── _compute_uptime helper ────────────────────────────────────────────────────

def test_compute_uptime_no_errors_is_100():
    from app.routes.devices import _compute_uptime
    assert _compute_uptime("dev", []) == 100.0


def test_compute_uptime_with_resolved_error():
    from app.routes.devices import _compute_uptime
    now = datetime.now(timezone.utc)
    error = Mock()
    error.occurred_at = now - timedelta(hours=1)
    error.resolved_at = now - timedelta(minutes=30)
    result = _compute_uptime("dev", [error])
    # 30-minute error over 30-day window → very close to 100%
    assert 99.9 <= result < 100.0


def test_compute_uptime_with_open_error():
    from app.routes.devices import _compute_uptime
    now = datetime.now(timezone.utc)
    error = Mock()
    error.occurred_at = now - timedelta(hours=24)
    error.resolved_at = None  # still open
    result = _compute_uptime("dev", [error])
    # 24-hour error over 30 days → ~96.7%
    assert result < 100.0
    assert result > 90.0


def test_compute_uptime_full_window_down_is_zero():
    from app.routes.devices import _compute_uptime
    now = datetime.now(timezone.utc)
    error = Mock()
    error.occurred_at = now - timedelta(days=35)  # started before the 30-day window
    error.resolved_at = None  # still open
    result = _compute_uptime("dev", [error])
    assert result == 0.0


# ── device status — site/org fields ──────────────────────────────────────────

def test_device_status_includes_site_fields(client, auth_headers, registered_device):
    device_id, _ = registered_device
    resp = client.get(f"/api/devices/{device_id}/status", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "site_id" in data
    assert "site_nickname" in data
    assert "organization_id" in data
    assert "organization_name" in data
    assert data["site_id"] is None


def test_list_devices_includes_site_fields(client, auth_headers, registered_device):
    resp = client.get("/api/devices", headers=auth_headers)
    device_id, _ = registered_device
    devices = resp.json()["devices"]
    device = next(d for d in devices if d["device_id"] == device_id)
    assert "site_id" in device
    assert "site_nickname" in device
    assert "organization_name" in device


# ── heartbeat online_since tracking ──────────────────────────────────────────

def test_heartbeat_sets_online_since_on_first_online(client, auth_headers, device_api_headers):
    device_id, api_headers = device_api_headers
    client.patch(f"/api/devices/{device_id}/heartbeat",
                 json={"online": True}, headers=api_headers)
    status = client.get(f"/api/devices/{device_id}/status", headers=auth_headers).json()
    assert status["online_since"] is not None


def test_heartbeat_clears_online_since_when_offline(client, auth_headers, device_api_headers):
    device_id, api_headers = device_api_headers
    client.patch(f"/api/devices/{device_id}/heartbeat", json={"online": True}, headers=api_headers)
    client.patch(f"/api/devices/{device_id}/heartbeat", json={"online": False}, headers=api_headers)
    status = client.get(f"/api/devices/{device_id}/status", headers=auth_headers).json()
    assert status["online_since"] is None


# ── Bug: sort_by=uptime_percent silently sorts by device_id ───────────────────

def test_sort_by_uptime_percent_orders_by_computed_uptime(client, auth_headers, db_session):
    """sort_by=uptime_percent must sort by uptime, not fall back to device_id.

    'aaa-uptest' has no errors (100% uptime).
    'zzz-uptest' has a 24-hour open error (~96.7% uptime).
    Alphabetical order puts aaa first; correct uptime ASC puts zzz first.
    The bug: getattr(Device, 'uptime_percent', Device.device_id) returns Device.device_id
    because uptime_percent is not a model column, so the sort silently does nothing.
    """
    now = datetime.now(timezone.utc)
    db_session.add(Device(device_id="aaa-uptest", api_key="k-aaa"))
    db_session.add(Device(device_id="zzz-uptest", api_key="k-zzz"))
    db_session.commit()
    db_session.add(DeviceErrorHistory(
        device_id="zzz-uptest",
        occurred_at=now - timedelta(hours=24),
        resolved_at=None,
    ))
    db_session.commit()

    resp = client.get("/api/devices?sort_by=uptime_percent&sort_order=asc", headers=auth_headers)
    assert resp.status_code == 200
    devices = resp.json()["devices"]
    relevant = [d for d in devices if d["device_id"] in {"aaa-uptest", "zzz-uptest"}]
    assert len(relevant) == 2
    # zzz-uptest has the lower uptime and must appear first in ascending order
    assert relevant[0]["device_id"] == "zzz-uptest", (
        f"Expected zzz-uptest (lower uptime) first, got {relevant[0]['device_id']}. "
        "sort_by=uptime_percent is likely falling back to device_id sort."
    )


# ── Bug: sort_by with a non-column attribute crashes with 500 ─────────────────

def test_sort_by_invalid_field_rejected_not_500(client, auth_headers):
    """sort_by values that aren't valid Device columns must be rejected (4xx), not crash (500).

    getattr(Device, '__tablename__') returns the string 'devices'.
    query.order_by('devices'.desc()) raises AttributeError → unhandled 500.
    The fix is an allowlist; the test expects a 422.
    """
    resp = client.get("/api/devices?sort_by=__tablename__&sort_order=desc", headers=auth_headers)
    assert resp.status_code == 422, (
        f"Expected 422 for invalid sort_by, got {resp.status_code}. "
        "sort_by has no allowlist — non-column attributes can crash the server."
    )


def test_sort_by_unknown_name_rejected_not_silently_ignored(client, auth_headers):
    """A misspelled sort_by like 'lastseen' should be a 422, not silently sort by device_id."""
    resp = client.get("/api/devices?sort_by=lastseen", headers=auth_headers)
    assert resp.status_code == 422


# ── Bug: _compute_uptime double-counts overlapping error intervals ─────────────

def test_compute_uptime_overlapping_errors_not_double_counted():
    """Overlapping error windows must be merged before summing downtime.

    Error 1: T-2h → T-30min  (90 min of downtime)
    Error 2: T-90min → T-30min  (60 min, fully inside Error 1's window)
    Real downtime: 90 min (the union of both intervals).
    Naive sum: 150 min → understates uptime by 60 min.
    Correct uptime over 30 days: ~99.8%.  Buggy result: ~99.7%.
    """
    from app.routes.devices import _compute_uptime
    now = datetime.now(timezone.utc)

    e1 = Mock()
    e1.occurred_at = now - timedelta(hours=2)
    e1.resolved_at = now - timedelta(minutes=30)

    e2 = Mock()
    e2.occurred_at = now - timedelta(minutes=90)  # starts inside e1
    e2.resolved_at = now - timedelta(minutes=30)   # same end

    result = _compute_uptime("dev", [e1, e2])
    # Correct: 90 min downtime / 30-day window → 99.79% → rounds to 99.8
    # Bug returns: 150 min / 30-day window → 99.65% → rounds to 99.7
    assert result == pytest.approx(99.8, abs=0.05), (
        f"Got {result}. Overlapping errors are being double-counted "
        "(naive sum instead of merging intervals)."
    )
