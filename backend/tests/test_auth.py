"""Tests for authentication endpoints."""


def test_login_success(client):
    resp = client.post("/api/auth/login", json={"username": "admin", "password": "support123"})
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert len(data["access_token"]) > 20


def test_login_wrong_password(client):
    resp = client.post("/api/auth/login", json={"username": "admin", "password": "wrongpassword"})
    assert resp.status_code == 401
    assert "Invalid" in resp.json()["detail"]


def test_login_unknown_user(client):
    resp = client.post("/api/auth/login", json={"username": "nobody", "password": "support123"})
    assert resp.status_code == 401
    assert "Invalid" in resp.json()["detail"]


def test_login_empty_password(client):
    resp = client.post("/api/auth/login", json={"username": "admin", "password": ""})
    assert resp.status_code == 401


def test_login_returns_usable_token(client):
    token = client.post("/api/auth/login", json={"username": "admin", "password": "support123"}).json()["access_token"]
    resp = client.get("/api/devices", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200


def test_protected_route_rejects_bad_token(client):
    resp = client.get("/api/devices", headers={"Authorization": "Bearer bad.token.here"})
    assert resp.status_code == 401


def test_protected_route_rejects_missing_auth(client):
    resp = client.get("/api/devices")
    assert resp.status_code == 401
