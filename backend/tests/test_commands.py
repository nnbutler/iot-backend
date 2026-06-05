"""Tests for command sending, listing, and result reporting."""
import pytest


# ─── GET /api/commands/available ──────────────────────────────────────────────


def test_list_available_commands_requires_auth(client):
    assert client.get("/api/commands/available").status_code == 401


def test_list_available_commands_returns_all_four(client, auth_headers):
    resp = client.get("/api/commands/available", headers=auth_headers)
    assert resp.status_code == 200
    types = {c["command_type"] for c in resp.json()["commands"]}
    assert types == {"restart_plc", "reset_state_machine", "reboot_device", "clear_error_log"}


def test_list_available_commands_have_labels(client, auth_headers):
    commands = client.get("/api/commands/available", headers=auth_headers).json()["commands"]
    for cmd in commands:
        assert "command_type" in cmd
        assert "label" in cmd
        assert len(cmd["label"]) > 0


# ─── POST /api/devices/{device_id}/commands ───────────────────────────────────


def test_send_command_requires_auth(client, registered_device):
    device_id, _ = registered_device
    resp = client.post(f"/api/devices/{device_id}/commands", json={"command_type": "restart_plc"})
    assert resp.status_code == 401


def test_send_command_success(client, auth_headers, registered_device):
    device_id, _ = registered_device
    resp = client.post(f"/api/devices/{device_id}/commands", headers=auth_headers,
                       json={"command_type": "restart_plc"})
    assert resp.status_code == 201
    data = resp.json()
    assert data["device_id"] == device_id
    assert data["command_type"] == "restart_plc"
    assert data["status"] == "sent"
    assert data["sent_by"] == "support"
    assert data["label"] == "Restart PLC"
    assert "id" in data
    assert "sent_at" in data


def test_send_command_device_not_found(client, auth_headers):
    resp = client.post("/api/devices/nonexistent/commands", headers=auth_headers,
                       json={"command_type": "restart_plc"})
    assert resp.status_code == 404


def test_send_command_invalid_type_returns_422(client, auth_headers, registered_device):
    device_id, _ = registered_device
    resp = client.post(f"/api/devices/{device_id}/commands", headers=auth_headers,
                       json={"command_type": "rm_rf_slash"})
    assert resp.status_code == 422
    assert "Unknown command" in resp.json()["detail"]


def test_send_command_missing_type_returns_422(client, auth_headers, registered_device):
    device_id, _ = registered_device
    resp = client.post(f"/api/devices/{device_id}/commands", headers=auth_headers, json={})
    assert resp.status_code == 422


def test_send_command_all_valid_types_accepted(client, auth_headers, registered_device):
    device_id, _ = registered_device
    for cmd in ("restart_plc", "reset_state_machine", "reboot_device", "clear_error_log"):
        resp = client.post(f"/api/devices/{device_id}/commands", headers=auth_headers,
                           json={"command_type": cmd})
        assert resp.status_code == 201, f"Expected 201 for {cmd}, got {resp.status_code}"


def test_send_command_logged_with_correct_username(client, other_user_headers, registered_device):
    device_id, _ = registered_device
    resp = client.post(f"/api/devices/{device_id}/commands", headers=other_user_headers,
                       json={"command_type": "restart_plc"})
    assert resp.json()["sent_by"] == "alice"


def test_send_command_initial_status_is_sent(client, auth_headers, registered_device):
    device_id, _ = registered_device
    resp = client.post(f"/api/devices/{device_id}/commands", headers=auth_headers,
                       json={"command_type": "reboot_device"})
    assert resp.json()["status"] == "sent"


# ─── GET /api/devices/{device_id}/commands ────────────────────────────────────


def test_list_device_commands_requires_auth(client, registered_device):
    device_id, _ = registered_device
    assert client.get(f"/api/devices/{device_id}/commands").status_code == 401


def test_list_device_commands_empty(client, auth_headers, registered_device):
    device_id, _ = registered_device
    resp = client.get(f"/api/devices/{device_id}/commands", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json() == {"commands": []}


def test_list_device_commands_after_send(client, auth_headers, registered_device):
    device_id, _ = registered_device
    client.post(f"/api/devices/{device_id}/commands", headers=auth_headers,
                json={"command_type": "restart_plc"})
    commands = client.get(f"/api/devices/{device_id}/commands", headers=auth_headers).json()["commands"]
    assert len(commands) == 1
    assert commands[0]["command_type"] == "restart_plc"


def test_list_device_commands_most_recent_first(client, auth_headers, registered_device):
    device_id, _ = registered_device
    for cmd in ("restart_plc", "clear_error_log", "reset_state_machine"):
        client.post(f"/api/devices/{device_id}/commands", headers=auth_headers,
                    json={"command_type": cmd})
    commands = client.get(f"/api/devices/{device_id}/commands", headers=auth_headers).json()["commands"]
    assert commands[0]["command_type"] == "reset_state_machine"


def test_list_device_commands_device_not_found(client, auth_headers):
    assert client.get("/api/devices/ghost/commands", headers=auth_headers).status_code == 404


def test_list_device_commands_response_shape(client, auth_headers, registered_device):
    device_id, _ = registered_device
    client.post(f"/api/devices/{device_id}/commands", headers=auth_headers,
                json={"command_type": "restart_plc"})
    cmd = client.get(f"/api/devices/{device_id}/commands", headers=auth_headers).json()["commands"][0]
    for field in ("id", "command_type", "label", "status", "result",
                  "error_message", "sent_by", "sent_at", "executed_at"):
        assert field in cmd, f"missing field: {field}"


def test_list_device_commands_limit_param(client, auth_headers, registered_device):
    device_id, _ = registered_device
    for _ in range(5):
        client.post(f"/api/devices/{device_id}/commands", headers=auth_headers,
                    json={"command_type": "restart_plc"})
    commands = client.get(f"/api/devices/{device_id}/commands?limit=3",
                          headers=auth_headers).json()["commands"]
    assert len(commands) == 3


# ─── PATCH /api/commands/{command_id} ─────────────────────────────────────────


def _send_command(client, auth_headers, device_id) -> int:
    resp = client.post(f"/api/devices/{device_id}/commands", headers=auth_headers,
                       json={"command_type": "restart_plc"})
    return resp.json()["id"]


def test_update_command_result_requires_api_key(client, auth_headers, registered_device):
    device_id, _ = registered_device
    cmd_id = _send_command(client, auth_headers, device_id)
    resp = client.patch(f"/api/commands/{cmd_id}", json={"status": "success"})
    assert resp.status_code == 401


def test_update_command_result_rejects_wrong_api_key(client, auth_headers, registered_device):
    device_id, _ = registered_device
    cmd_id = _send_command(client, auth_headers, device_id)
    resp = client.patch(f"/api/commands/{cmd_id}",
                        headers={"Authorization": "Bearer wrong-key"},
                        json={"status": "success"})
    assert resp.status_code == 401


def test_update_command_result_success(client, auth_headers, device_api_headers):
    device_id, api_headers = device_api_headers
    cmd_id = _send_command(client, auth_headers, device_id)
    resp = client.patch(f"/api/commands/{cmd_id}", headers=api_headers,
                        json={"status": "success", "result": "PLC restarted"})
    assert resp.status_code == 200
    assert resp.json()["status"] == "success"
    assert resp.json()["id"] == cmd_id


def test_update_command_result_failed(client, auth_headers, device_api_headers):
    device_id, api_headers = device_api_headers
    cmd_id = _send_command(client, auth_headers, device_id)
    resp = client.patch(f"/api/commands/{cmd_id}", headers=api_headers,
                        json={"status": "failed", "error_message": "Timeout waiting for PLC"})
    assert resp.status_code == 200
    assert resp.json()["status"] == "failed"


def test_update_command_result_executing(client, auth_headers, device_api_headers):
    device_id, api_headers = device_api_headers
    cmd_id = _send_command(client, auth_headers, device_id)
    resp = client.patch(f"/api/commands/{cmd_id}", headers=api_headers,
                        json={"status": "executing"})
    assert resp.status_code == 200
    assert resp.json()["status"] == "executing"


def test_update_command_result_sets_executed_at_on_terminal_status(client, auth_headers, device_api_headers, db_session):
    from app.models.command import Command
    device_id, api_headers = device_api_headers
    cmd_id = _send_command(client, auth_headers, device_id)
    client.patch(f"/api/commands/{cmd_id}", headers=api_headers, json={"status": "success"})

    db_session.expire_all()
    cmd = db_session.query(Command).filter(Command.id == cmd_id).first()
    assert cmd.executed_at is not None


def test_update_command_result_no_executed_at_while_executing(client, auth_headers, device_api_headers, db_session):
    from app.models.command import Command
    device_id, api_headers = device_api_headers
    cmd_id = _send_command(client, auth_headers, device_id)
    client.patch(f"/api/commands/{cmd_id}", headers=api_headers, json={"status": "executing"})

    db_session.expire_all()
    cmd = db_session.query(Command).filter(Command.id == cmd_id).first()
    assert cmd.executed_at is None


def test_update_command_result_invalid_status(client, auth_headers, device_api_headers):
    device_id, api_headers = device_api_headers
    cmd_id = _send_command(client, auth_headers, device_id)
    resp = client.patch(f"/api/commands/{cmd_id}", headers=api_headers,
                        json={"status": "banana"})
    assert resp.status_code == 422


def test_update_command_result_not_found(client, device_api_headers):
    _, api_headers = device_api_headers
    resp = client.patch("/api/commands/999999", headers=api_headers, json={"status": "success"})
    assert resp.status_code == 404


def test_update_command_result_persists_in_history(client, auth_headers, device_api_headers):
    device_id, api_headers = device_api_headers
    cmd_id = _send_command(client, auth_headers, device_id)
    client.patch(f"/api/commands/{cmd_id}", headers=api_headers,
                 json={"status": "success", "result": "Done"})
    commands = client.get(f"/api/devices/{device_id}/commands", headers=auth_headers).json()["commands"]
    cmd = next(c for c in commands if c["id"] == cmd_id)
    assert cmd["status"] == "success"
    assert cmd["result"] == "Done"
    assert cmd["executed_at"] is not None
