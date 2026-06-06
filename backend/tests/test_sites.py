"""Tests for site CRUD, geocoding, and comment endpoints."""
import pytest
from unittest.mock import patch, AsyncMock, Mock
from app.models.organization import Organization, Site, SiteComment
from app.models.device import Device


@pytest.fixture
def org(db_session):
    o = Organization(name="Test Org")
    db_session.add(o)
    db_session.commit()
    return o


@pytest.fixture
def site(db_session, org):
    s = Site(
        organization_id=org.id,
        nickname="Phoenix Plant",
        address="123 Main St, Phoenix AZ 85001",
        contact_name="Jane Smith",
        contact_phone="+1 602 555 0100",
        contact_email="jane@test.com",
        operating_hours="Mon-Fri 6am-10pm",
    )
    db_session.add(s)
    db_session.commit()
    return s


@pytest.fixture
def site_body(org):
    return {
        "organization_id": org.id,
        "nickname": "Phoenix Plant",
        "address": "123 Main St, Phoenix AZ 85001",
        "contact_name": "Jane Smith",
        "contact_phone": "+1 602 555 0100",
        "contact_email": "jane@test.com",
        "operating_hours": "Mon-Fri 6am-10pm",
    }


# ── List ──────────────────────────────────────────────────────────────────────

def test_list_sites_returns_list(client, auth_headers):
    resp = client.get("/api/sites", headers=auth_headers)
    assert resp.status_code == 200
    assert isinstance(resp.json()["sites"], list)


def test_list_sites_includes_created_site(client, auth_headers, site):
    resp = client.get("/api/sites", headers=auth_headers)
    assert resp.status_code == 200
    nicknames = [s["nickname"] for s in resp.json()["sites"]]
    assert "Phoenix Plant" in nicknames


def test_list_sites_requires_auth(client):
    resp = client.get("/api/sites")
    assert resp.status_code == 401


def test_list_sites_response_shape(client, auth_headers, site):
    s = client.get("/api/sites", headers=auth_headers).json()["sites"][0]
    for key in ["id", "organization_id", "organization_name", "nickname", "address",
                "contact_name", "contact_phone", "contact_email", "operating_hours",
                "latitude", "longitude", "timezone"]:
        assert key in s


# ── Create ────────────────────────────────────────────────────────────────────

def test_create_site(client, auth_headers, site_body):
    resp = client.post("/api/sites", json=site_body, headers=auth_headers)
    assert resp.status_code == 201
    data = resp.json()
    assert data["nickname"] == "Phoenix Plant"
    assert data["organization_name"] == "Test Org"


def test_create_site_with_geo(client, auth_headers, site_body):
    site_body.update({"latitude": 33.44, "longitude": -112.07, "timezone": "America/Phoenix"})
    resp = client.post("/api/sites", json=site_body, headers=auth_headers)
    assert resp.status_code == 201
    data = resp.json()
    assert data["latitude"] == pytest.approx(33.44)
    assert data["timezone"] == "America/Phoenix"


def test_create_site_invalid_org_returns_404(client, auth_headers, site_body):
    site_body["organization_id"] = 99999
    resp = client.post("/api/sites", json=site_body, headers=auth_headers)
    assert resp.status_code == 404


def test_create_site_requires_auth(client, site_body):
    resp = client.post("/api/sites", json=site_body)
    assert resp.status_code == 401


# ── Get ───────────────────────────────────────────────────────────────────────

def test_get_site(client, auth_headers, site):
    resp = client.get(f"/api/sites/{site.id}", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["nickname"] == "Phoenix Plant"
    assert "devices" in data


def test_get_site_includes_devices(client, auth_headers, site, db_session):
    device = Device(device_id="site-device-001", api_key="key", site_id=site.id)
    db_session.add(device)
    db_session.commit()
    resp = client.get(f"/api/sites/{site.id}", headers=auth_headers)
    devices = resp.json()["devices"]
    assert len(devices) == 1
    assert devices[0]["device_id"] == "site-device-001"


def test_get_site_not_found(client, auth_headers):
    resp = client.get("/api/sites/99999", headers=auth_headers)
    assert resp.status_code == 404


# ── Update ────────────────────────────────────────────────────────────────────

def test_update_site(client, auth_headers, site, org):
    resp = client.patch(f"/api/sites/{site.id}", json={
        "organization_id": org.id,
        "nickname": "Renamed Plant",
        "address": "456 Oak Ave",
        "contact_name": "Bob",
        "contact_phone": None,
        "contact_email": None,
        "operating_hours": None,
    }, headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["nickname"] == "Renamed Plant"
    assert resp.json()["address"] == "456 Oak Ave"


def test_update_site_not_found(client, auth_headers, org):
    resp = client.patch("/api/sites/99999", json={
        "organization_id": org.id,
        "nickname": "Ghost",
    }, headers=auth_headers)
    assert resp.status_code == 404


def test_update_site_invalid_org_returns_404(client, auth_headers, site):
    resp = client.patch(f"/api/sites/{site.id}", json={
        "organization_id": 99999,
        "nickname": site.nickname,
    }, headers=auth_headers)
    assert resp.status_code == 404


def test_update_site_preserves_geo_when_omitted(client, auth_headers, site, org, db_session):
    """PATCH without lat/lon/timezone must not wipe previously geocoded coordinates.

    SiteBody defaults latitude/longitude/timezone to None. The current handler
    blindly assigns body.latitude → site.latitude, so a PATCH that omits geo fields
    silently destroys geocoded data. The fix is to skip None geo fields on update.
    """
    site.latitude = 33.4484
    site.longitude = -112.0740
    site.timezone = "America/Phoenix"
    db_session.commit()

    resp = client.patch(f"/api/sites/{site.id}", json={
        "organization_id": org.id,
        "nickname": "Renamed Without Geo",
        "address": site.address,
    }, headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["latitude"] == pytest.approx(33.4484), (
        "latitude was wiped by PATCH — SiteBody defaults to None and handler assigns unconditionally"
    )
    assert data["longitude"] == pytest.approx(-112.0740)
    assert data["timezone"] == "America/Phoenix"


# ── Delete ────────────────────────────────────────────────────────────────────

def test_delete_site(client, auth_headers, site):
    resp = client.delete(f"/api/sites/{site.id}", headers=auth_headers)
    assert resp.status_code == 204
    assert client.get(f"/api/sites/{site.id}", headers=auth_headers).status_code == 404


def test_delete_site_not_found(client, auth_headers):
    resp = client.delete("/api/sites/99999", headers=auth_headers)
    assert resp.status_code == 404


def test_delete_site_sets_device_site_null(client, auth_headers, site, db_session):
    device = Device(device_id="orphan-device", api_key="key2", site_id=site.id)
    db_session.add(device)
    db_session.commit()
    client.delete(f"/api/sites/{site.id}", headers=auth_headers)
    db_session.refresh(device)
    assert device.site_id is None


# ── Geocode ───────────────────────────────────────────────────────────────────

def test_geocode_site(client, auth_headers, site):
    # httpx response.json() is synchronous, so use a plain Mock for the response
    mock_response = Mock()
    mock_response.json.return_value = [{"lat": "33.4484", "lon": "-112.0740"}]
    mock_response.raise_for_status = Mock()

    with patch("app.routes.sites.httpx.AsyncClient") as mock_client_cls:
        mock_async_client = AsyncMock()
        mock_async_client.__aenter__ = AsyncMock(return_value=mock_async_client)
        mock_async_client.__aexit__ = AsyncMock(return_value=None)
        mock_async_client.get = AsyncMock(return_value=mock_response)
        mock_client_cls.return_value = mock_async_client

        with patch("app.routes.sites.TimezoneFinder") as mock_tf:
            mock_tf.return_value.timezone_at.return_value = "America/Phoenix"
            resp = client.post(f"/api/sites/{site.id}/geocode", headers=auth_headers)

    assert resp.status_code == 200
    data = resp.json()
    assert data["latitude"] == pytest.approx(33.4484)
    assert data["longitude"] == pytest.approx(-112.0740)
    assert data["timezone"] == "America/Phoenix"


def test_geocode_site_no_address(client, auth_headers, db_session, org):
    s = Site(organization_id=org.id, nickname="No Address Site")
    db_session.add(s)
    db_session.commit()
    resp = client.post(f"/api/sites/{s.id}/geocode", headers=auth_headers)
    assert resp.status_code == 400


def test_geocode_site_not_found(client, auth_headers):
    resp = client.post("/api/sites/99999/geocode", headers=auth_headers)
    assert resp.status_code == 404


def test_geocode_address_not_found(client, auth_headers, site):
    mock_response = Mock()
    mock_response.json.return_value = []
    mock_response.raise_for_status = Mock()

    with patch("app.routes.sites.httpx.AsyncClient") as mock_client_cls:
        mock_async_client = AsyncMock()
        mock_async_client.__aenter__ = AsyncMock(return_value=mock_async_client)
        mock_async_client.__aexit__ = AsyncMock(return_value=None)
        mock_async_client.get = AsyncMock(return_value=mock_response)
        mock_client_cls.return_value = mock_async_client
        resp = client.post(f"/api/sites/{site.id}/geocode", headers=auth_headers)

    assert resp.status_code == 404


# ── Device assignment ─────────────────────────────────────────────────────────

def test_assign_device_to_site(client, auth_headers, site, db_session):
    device = Device(device_id="assign-device", api_key="akey")
    db_session.add(device)
    db_session.commit()
    resp = client.patch(f"/api/sites/{site.id}/devices/assign-device", headers=auth_headers)
    assert resp.status_code == 200
    db_session.refresh(device)
    assert device.site_id == site.id


def test_unassign_device_from_site(client, auth_headers, site, db_session):
    device = Device(device_id="unassign-device", api_key="ukey", site_id=site.id)
    db_session.add(device)
    db_session.commit()
    resp = client.delete(f"/api/sites/{site.id}/devices/unassign-device", headers=auth_headers)
    assert resp.status_code == 204
    db_session.refresh(device)
    assert device.site_id is None


# ── Comments ──────────────────────────────────────────────────────────────────

def test_list_comments_empty(client, auth_headers, site):
    resp = client.get(f"/api/sites/{site.id}/comments", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["comments"] == []


def test_add_comment(client, auth_headers, site):
    resp = client.post(f"/api/sites/{site.id}/comments",
                       json={"body": "Check the east sensor weekly."},
                       headers=auth_headers)
    assert resp.status_code == 201
    data = resp.json()
    assert data["body"] == "Check the east sensor weekly."
    assert data["username"] == "support"
    assert "created_at" in data


def test_list_comments_newest_first(client, auth_headers, site, db_session):
    db_session.add(SiteComment(site_id=site.id, username="support", body="First note"))
    db_session.add(SiteComment(site_id=site.id, username="support", body="Second note"))
    db_session.commit()
    resp = client.get(f"/api/sites/{site.id}/comments", headers=auth_headers)
    comments = resp.json()["comments"]
    assert comments[0]["body"] == "Second note"
    assert comments[1]["body"] == "First note"


def test_add_empty_comment_returns_400(client, auth_headers, site):
    resp = client.post(f"/api/sites/{site.id}/comments",
                       json={"body": "   "},
                       headers=auth_headers)
    assert resp.status_code == 400


def test_delete_own_comment(client, auth_headers, site, db_session):
    comment = SiteComment(site_id=site.id, username="support", body="My note")
    db_session.add(comment)
    db_session.commit()
    resp = client.delete(f"/api/sites/{site.id}/comments/{comment.id}", headers=auth_headers)
    assert resp.status_code == 204


def test_delete_other_users_comment_returns_403(client, auth_headers, other_user_headers, site, db_session):
    comment = SiteComment(site_id=site.id, username="alice", body="Alice's note")
    db_session.add(comment)
    db_session.commit()
    resp = client.delete(f"/api/sites/{site.id}/comments/{comment.id}", headers=auth_headers)
    assert resp.status_code == 403


def test_comments_require_auth(client, site):
    assert client.get(f"/api/sites/{site.id}/comments").status_code == 401
    assert client.post(f"/api/sites/{site.id}/comments", json={"body": "x"}).status_code == 401


def test_comments_site_not_found(client, auth_headers):
    assert client.get("/api/sites/99999/comments", headers=auth_headers).status_code == 404
    assert client.post("/api/sites/99999/comments", json={"body": "x"}, headers=auth_headers).status_code == 404


def test_geocode_service_unavailable_returns_502(client, auth_headers, site):
    with patch("app.routes.sites.httpx.AsyncClient") as mock_client_cls:
        mock_async_client = AsyncMock()
        mock_async_client.__aenter__ = AsyncMock(return_value=mock_async_client)
        mock_async_client.__aexit__ = AsyncMock(return_value=None)
        mock_async_client.get = AsyncMock(side_effect=Exception("connection refused"))
        mock_client_cls.return_value = mock_async_client
        resp = client.post(f"/api/sites/{site.id}/geocode", headers=auth_headers)
    assert resp.status_code == 502


def test_unassign_device_not_on_this_site_returns_404(client, auth_headers, site, db_session):
    other_site = Site(organization_id=site.organization_id, nickname="Other")
    db_session.add(other_site)
    device = Device(device_id="wrong-site-device", api_key="wkey", site_id=other_site.id)
    db_session.add(device)
    db_session.commit()
    # Try to unassign from a site the device doesn't belong to
    resp = client.delete(f"/api/sites/{site.id}/devices/wrong-site-device", headers=auth_headers)
    assert resp.status_code == 404
