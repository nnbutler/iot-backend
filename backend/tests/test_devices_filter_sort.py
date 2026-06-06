"""Tests for device filtering and sorting."""
import pytest


@pytest.fixture
def test_devices(client, auth_headers, db_session):
    """Create diverse test devices for filtering/sorting tests."""
    from app.models.device import Device
    import secrets

    devices_data = [
        ("plc-alpha", "Acme Inc", "Phoenix, AZ", True, None),
        ("plc-beta", "Acme Inc", "Denver, CO", False, "sensor_disconnected"),
        ("plc-gamma", "Beta Corp", "Seattle, WA", True, None),
        ("plc-delta", "Gamma Ltd", "Austin, TX", False, "internet_down"),
    ]

    for device_id, customer, location, online, error in devices_data:
        device = Device(
            device_id=device_id,
            api_key=secrets.token_urlsafe(32),  # Unique key for each device
            customer_name=customer,
            location=location,
            online=online,
            last_error=error,
        )
        db_session.add(device)
    db_session.commit()

    # Return for use in tests
    return {d[0]: d for d in devices_data}


# ─── Search Filtering Tests ───────────────────────────────────────────────────


def test_filter_search_by_device_id(client, auth_headers, test_devices):
    """Test search filter by device ID."""
    resp = client.get("/api/devices?search=plc-alpha", headers=auth_headers)
    assert resp.status_code == 200
    devices = resp.json()["devices"]
    assert len(devices) == 1
    assert devices[0]["device_id"] == "plc-alpha"


def test_filter_search_by_customer_name(client, auth_headers, test_devices):
    """Test search filter by customer name."""
    resp = client.get("/api/devices?search=Acme", headers=auth_headers)
    assert resp.status_code == 200
    devices = resp.json()["devices"]
    assert len(devices) == 2
    ids = {d["device_id"] for d in devices}
    assert ids == {"plc-alpha", "plc-beta"}


def test_filter_search_by_location(client, auth_headers, test_devices):
    """Test search filter by location."""
    resp = client.get("/api/devices?search=Seattle", headers=auth_headers)
    assert resp.status_code == 200
    devices = resp.json()["devices"]
    assert len(devices) == 1
    assert devices[0]["device_id"] == "plc-gamma"


def test_filter_search_case_insensitive(client, auth_headers, test_devices):
    """Test search filter is case-insensitive."""
    resp = client.get("/api/devices?search=ACME", headers=auth_headers)
    assert resp.status_code == 200
    devices = resp.json()["devices"]
    assert len(devices) == 2


def test_filter_search_no_match(client, auth_headers, test_devices):
    """Test search filter with no matches."""
    resp = client.get("/api/devices?search=nonexistent", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["devices"] == []


# ─── Status Filtering Tests ───────────────────────────────────────────────────


def test_filter_by_online_true(client, auth_headers, test_devices):
    """Test filter for online devices."""
    resp = client.get("/api/devices?online=true", headers=auth_headers)
    assert resp.status_code == 200
    devices = resp.json()["devices"]
    assert len(devices) == 2
    assert all(d["online"] is True for d in devices)
    ids = {d["device_id"] for d in devices}
    assert ids == {"plc-alpha", "plc-gamma"}


def test_filter_by_online_false(client, auth_headers, test_devices):
    """Test filter for offline devices."""
    resp = client.get("/api/devices?online=false", headers=auth_headers)
    assert resp.status_code == 200
    devices = resp.json()["devices"]
    assert len(devices) == 2
    assert all(d["online"] is False for d in devices)
    ids = {d["device_id"] for d in devices}
    assert ids == {"plc-beta", "plc-delta"}


# ─── Customer Filtering Tests ─────────────────────────────────────────────────


def test_filter_by_customer(client, auth_headers, test_devices):
    """Test filter by specific customer name."""
    resp = client.get("/api/devices?customer=Beta%20Corp", headers=auth_headers)
    assert resp.status_code == 200
    devices = resp.json()["devices"]
    assert len(devices) == 1
    assert devices[0]["customer_name"] == "Beta Corp"


def test_filter_by_customer_case_insensitive(client, auth_headers, test_devices):
    """Test customer filter is case-insensitive."""
    resp = client.get("/api/devices?customer=gamma", headers=auth_headers)
    assert resp.status_code == 200
    devices = resp.json()["devices"]
    assert len(devices) == 1
    assert devices[0]["device_id"] == "plc-delta"


# ─── Error Filtering Tests ────────────────────────────────────────────────────


def test_filter_has_error_true(client, auth_headers, test_devices):
    """Test filter for devices with errors."""
    resp = client.get("/api/devices?has_error=true", headers=auth_headers)
    assert resp.status_code == 200
    devices = resp.json()["devices"]
    assert len(devices) == 2
    assert all(d["last_error"] is not None for d in devices)
    ids = {d["device_id"] for d in devices}
    assert ids == {"plc-beta", "plc-delta"}


def test_filter_has_error_false(client, auth_headers, test_devices):
    """Test filter for healthy devices (no errors)."""
    resp = client.get("/api/devices?has_error=false", headers=auth_headers)
    assert resp.status_code == 200
    devices = resp.json()["devices"]
    assert len(devices) == 2
    assert all(d["last_error"] is None for d in devices)
    ids = {d["device_id"] for d in devices}
    assert ids == {"plc-alpha", "plc-gamma"}


# ─── Sorting Tests ────────────────────────────────────────────────────────────


def test_sort_by_device_id_asc(client, auth_headers, test_devices):
    """Test sort by device_id ascending."""
    resp = client.get("/api/devices?sort_by=device_id&sort_order=asc", headers=auth_headers)
    assert resp.status_code == 200
    devices = resp.json()["devices"]
    ids = [d["device_id"] for d in devices]
    assert ids == sorted(ids)


def test_sort_by_device_id_desc(client, auth_headers, test_devices):
    """Test sort by device_id descending."""
    resp = client.get("/api/devices?sort_by=device_id&sort_order=desc", headers=auth_headers)
    assert resp.status_code == 200
    devices = resp.json()["devices"]
    ids = [d["device_id"] for d in devices]
    assert ids == sorted(ids, reverse=True)


def test_sort_by_customer_name(client, auth_headers, test_devices):
    """Test sort by customer name."""
    resp = client.get("/api/devices?sort_by=customer_name&sort_order=asc", headers=auth_headers)
    assert resp.status_code == 200
    devices = resp.json()["devices"]
    names = [d["customer_name"] for d in devices]
    assert names == sorted(names)


def test_sort_by_online_status(client, auth_headers, test_devices):
    """Test sort by online status."""
    resp = client.get("/api/devices?sort_by=online&sort_order=asc", headers=auth_headers)
    assert resp.status_code == 200
    devices = resp.json()["devices"]
    statuses = [d["online"] for d in devices]
    assert statuses == sorted(statuses)


def test_sort_by_last_error(client, auth_headers, test_devices):
    """Test sort by last_error field."""
    resp = client.get("/api/devices?sort_by=last_error&sort_order=asc", headers=auth_headers)
    assert resp.status_code == 200
    devices = resp.json()["devices"]
    # Should work without errors
    assert len(devices) == 4


def test_sort_default_is_device_id_asc(client, auth_headers, test_devices):
    """Test default sort is by device_id ascending."""
    resp = client.get("/api/devices", headers=auth_headers)
    assert resp.status_code == 200
    devices = resp.json()["devices"]
    ids = [d["device_id"] for d in devices]
    assert ids == sorted(ids)


# ─── Combined Filter + Sort Tests ─────────────────────────────────────────────


def test_filter_and_sort_combined(client, auth_headers, test_devices):
    """Test combining filter and sort."""
    resp = client.get(
        "/api/devices?online=true&sort_by=customer_name&sort_order=desc",
        headers=auth_headers
    )
    assert resp.status_code == 200
    devices = resp.json()["devices"]

    # Should have 2 online devices
    assert len(devices) == 2
    assert all(d["online"] is True for d in devices)

    # Should be sorted by customer name descending
    names = [d["customer_name"] for d in devices]
    assert names == sorted(names, reverse=True)


def test_search_and_error_filter_combined(client, auth_headers, test_devices):
    """Test combining search and error filter."""
    resp = client.get(
        "/api/devices?search=Acme&has_error=true",
        headers=auth_headers
    )
    assert resp.status_code == 200
    devices = resp.json()["devices"]

    # Only plc-beta matches both filters
    assert len(devices) == 1
    assert devices[0]["device_id"] == "plc-beta"


def test_all_filters_combined(client, auth_headers, test_devices):
    """Test using all filters together."""
    resp = client.get(
        "/api/devices?search=plc&online=true&customer=Acme&has_error=false&sort_by=device_id&sort_order=desc",
        headers=auth_headers
    )
    assert resp.status_code == 200
    devices = resp.json()["devices"]

    # Only plc-alpha matches all filters
    assert len(devices) == 1
    assert devices[0]["device_id"] == "plc-alpha"


# ─── Invalid Parameters Tests ────────────────────────────────────────────────


def test_invalid_sort_field_returns_422(client, auth_headers, test_devices):
    """Invalid sort_by field is rejected with 422 (allowlist enforced)."""
    resp = client.get("/api/devices?sort_by=invalid_field", headers=auth_headers)
    assert resp.status_code == 422


def test_invalid_sort_order_uses_default(client, auth_headers, test_devices):
    """Test invalid sort order uses default ascending."""
    resp = client.get("/api/devices?sort_by=device_id&sort_order=invalid", headers=auth_headers)
    assert resp.status_code == 200
    devices = resp.json()["devices"]
    ids = [d["device_id"] for d in devices]
    # Should default to ascending
    assert ids == sorted(ids)
