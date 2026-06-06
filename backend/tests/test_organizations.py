"""Tests for organization CRUD endpoints."""
import pytest
from app.models.organization import Organization


@pytest.fixture
def org(db_session):
    o = Organization(name="Acme Corp")
    db_session.add(o)
    db_session.commit()
    return o


# ── List ──────────────────────────────────────────────────────────────────────

def test_list_orgs_returns_list(client, auth_headers):
    resp = client.get("/api/organizations", headers=auth_headers)
    assert resp.status_code == 200
    assert isinstance(resp.json()["organizations"], list)


def test_list_orgs_includes_created_org(client, auth_headers, org):
    resp = client.get("/api/organizations", headers=auth_headers)
    assert resp.status_code == 200
    names = [o["name"] for o in resp.json()["organizations"]]
    assert "Acme Corp" in names


def test_list_orgs_requires_auth(client):
    resp = client.get("/api/organizations")
    assert resp.status_code == 401


def test_list_orgs_response_shape(client, auth_headers, org):
    resp = client.get("/api/organizations", headers=auth_headers)
    o = resp.json()["organizations"][0]
    assert "id" in o
    assert "name" in o
    assert "logo_url" in o
    assert "website" in o
    assert "created_at" in o


# ── Create ────────────────────────────────────────────────────────────────────

def test_create_org(client, auth_headers):
    resp = client.post("/api/organizations", json={"name": "New Org"}, headers=auth_headers)
    assert resp.status_code == 201
    assert resp.json()["name"] == "New Org"


def test_create_org_with_logo_and_website(client, auth_headers):
    resp = client.post("/api/organizations", json={
        "name": "Branded Org",
        "logo_url": "https://example.com/logo.png",
        "website": "https://example.com",
    }, headers=auth_headers)
    assert resp.status_code == 201
    data = resp.json()
    assert data["logo_url"] == "https://example.com/logo.png"
    assert data["website"] == "https://example.com"


def test_create_org_duplicate_name_returns_409(client, auth_headers, org):
    resp = client.post("/api/organizations", json={"name": "Acme Corp"}, headers=auth_headers)
    assert resp.status_code == 409


def test_create_org_requires_auth(client):
    resp = client.post("/api/organizations", json={"name": "Anon Org"})
    assert resp.status_code == 401


# ── Get ───────────────────────────────────────────────────────────────────────

def test_get_org(client, auth_headers, org):
    resp = client.get(f"/api/organizations/{org.id}", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["name"] == "Acme Corp"


def test_get_org_not_found(client, auth_headers):
    resp = client.get("/api/organizations/99999", headers=auth_headers)
    assert resp.status_code == 404


# ── Update ────────────────────────────────────────────────────────────────────

def test_update_org_name(client, auth_headers, org):
    resp = client.patch(f"/api/organizations/{org.id}", json={"name": "Acme LLC"}, headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["name"] == "Acme LLC"


def test_update_org_adds_website(client, auth_headers, org):
    resp = client.patch(f"/api/organizations/{org.id}", json={
        "name": org.name,
        "website": "https://acme.com",
    }, headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["website"] == "https://acme.com"


def test_update_org_clears_website(client, auth_headers, db_session):
    o = Organization(name="Has Website", website="https://old.com")
    db_session.add(o)
    db_session.commit()
    resp = client.patch(f"/api/organizations/{o.id}", json={"name": "Has Website", "website": None}, headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["website"] is None


def test_update_org_duplicate_name_returns_409(client, auth_headers, org, db_session):
    other = Organization(name="Other Corp")
    db_session.add(other)
    db_session.commit()
    resp = client.patch(f"/api/organizations/{other.id}", json={"name": "Acme Corp"}, headers=auth_headers)
    assert resp.status_code == 409


def test_update_org_not_found(client, auth_headers):
    resp = client.patch("/api/organizations/99999", json={"name": "Ghost"}, headers=auth_headers)
    assert resp.status_code == 404


# ── Delete ────────────────────────────────────────────────────────────────────

def test_delete_org(client, auth_headers, org):
    resp = client.delete(f"/api/organizations/{org.id}", headers=auth_headers)
    assert resp.status_code == 204
    assert client.get(f"/api/organizations/{org.id}", headers=auth_headers).status_code == 404


def test_delete_org_with_sites_returns_409(client, auth_headers, org, db_session):
    from app.models.organization import Site
    site = Site(organization_id=org.id, nickname="Plant A")
    db_session.add(site)
    db_session.commit()
    resp = client.delete(f"/api/organizations/{org.id}", headers=auth_headers)
    assert resp.status_code == 409


def test_delete_org_not_found(client, auth_headers):
    resp = client.delete("/api/organizations/99999", headers=auth_headers)
    assert resp.status_code == 404
