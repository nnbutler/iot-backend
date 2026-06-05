"""Tests for error types, repair actions, and outcome recording."""
import pytest


# ─── GET /api/errors ──────────────────────────────────────────────────────────


def test_list_errors_requires_auth(client):
    assert client.get("/api/errors").status_code == 401


def test_list_errors_returns_seeded_error_types(client, auth_headers):
    resp = client.get("/api/errors", headers=auth_headers)
    assert resp.status_code == 200
    codes = {et["error_code"] for et in resp.json()["error_types"]}
    assert {"sensor_disconnected", "photoeye_misaligned", "internet_down",
            "state_machine_stuck", "unknown_error"} <= codes


def test_list_errors_includes_repair_actions(client, auth_headers):
    resp = client.get("/api/errors", headers=auth_headers)
    sensor = next(et for et in resp.json()["error_types"]
                  if et["error_code"] == "sensor_disconnected")
    assert len(sensor["repair_actions"]) == 3


def test_list_errors_sorted_alphabetically_by_display_name(client, auth_headers):
    error_types = client.get("/api/errors", headers=auth_headers).json()["error_types"]
    names = [et["display_name"] for et in error_types]
    assert names == sorted(names)


def test_list_errors_response_shape(client, auth_headers):
    error_types = client.get("/api/errors", headers=auth_headers).json()["error_types"]
    et = error_types[0]
    for field in ("id", "error_code", "display_name", "description", "severity", "repair_actions"):
        assert field in et


def test_list_errors_repair_action_shape(client, auth_headers):
    sensor = next(
        et for et in client.get("/api/errors", headers=auth_headers).json()["error_types"]
        if et["error_code"] == "sensor_disconnected"
    )
    action = sensor["repair_actions"][0]
    for field in ("id", "step", "action", "description", "estimated_time",
                  "success_rate", "occurrences", "successful_occurrences"):
        assert field in action


# ─── GET /api/errors/{error_code} ─────────────────────────────────────────────


def test_get_error_type_requires_auth(client):
    assert client.get("/api/errors/sensor_disconnected").status_code == 401


def test_get_error_type_success(client, auth_headers):
    resp = client.get("/api/errors/sensor_disconnected", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["error_code"] == "sensor_disconnected"
    assert data["display_name"] == "Sensor Disconnected"
    assert data["severity"] == "medium"


def test_get_error_type_not_found(client, auth_headers):
    resp = client.get("/api/errors/no_such_error", headers=auth_headers)
    assert resp.status_code == 404


def test_get_error_type_repair_actions_ordered_by_step(client, auth_headers):
    actions = client.get("/api/errors/sensor_disconnected", headers=auth_headers).json()["repair_actions"]
    steps = [a["step"] for a in actions]
    assert steps == sorted(steps)


def test_get_error_type_repair_actions_have_correct_count(client, auth_headers):
    data = client.get("/api/errors/sensor_disconnected", headers=auth_headers).json()
    assert len(data["repair_actions"]) == 3

    data = client.get("/api/errors/photoeye_misaligned", headers=auth_headers).json()
    assert len(data["repair_actions"]) == 2

    data = client.get("/api/errors/unknown_error", headers=auth_headers).json()
    assert len(data["repair_actions"]) == 0


def test_get_error_type_initial_success_rate(client, auth_headers):
    actions = client.get("/api/errors/sensor_disconnected", headers=auth_headers).json()["repair_actions"]
    for a in actions:
        assert a["success_rate"] == 0.5
        assert a["occurrences"] == 0
        assert a["successful_occurrences"] == 0


# ─── POST /api/errors/{error_code}/outcomes ───────────────────────────────────


def test_record_outcome_requires_auth(client, registered_device):
    device_id, _ = registered_device
    resp = client.post("/api/errors/sensor_disconnected/outcomes",
                       json={"device_id": device_id, "worked": True})
    assert resp.status_code == 401


def test_record_outcome_success(client, auth_headers, registered_device):
    device_id, _ = registered_device
    resp = client.post("/api/errors/sensor_disconnected/outcomes", headers=auth_headers, json={
        "device_id": device_id,
        "repair_action_id": 1,
        "worked": True,
        "notes": "Cable was loose",
        "time_spent_minutes": 5,
    })
    assert resp.status_code == 201
    data = resp.json()
    assert data["worked"] is True
    assert data["recorded_by"] == "support"
    assert "id" in data


def test_record_outcome_failure(client, auth_headers, registered_device):
    device_id, _ = registered_device
    resp = client.post("/api/errors/sensor_disconnected/outcomes", headers=auth_headers, json={
        "device_id": device_id,
        "repair_action_id": 1,
        "worked": False,
    })
    assert resp.status_code == 201
    assert resp.json()["worked"] is False


def test_record_outcome_updates_action_occurrences(client, auth_headers, registered_device):
    device_id, _ = registered_device
    for worked in [True, True, False]:
        client.post("/api/errors/sensor_disconnected/outcomes", headers=auth_headers, json={
            "device_id": device_id,
            "repair_action_id": 1,
            "worked": worked,
        })
    actions = client.get("/api/errors/sensor_disconnected", headers=auth_headers).json()["repair_actions"]
    action = next(a for a in actions if a["id"] == 1)
    assert action["occurrences"] == 3
    assert action["successful_occurrences"] == 2


def test_record_outcome_success_rate_calculated_correctly(client, auth_headers, registered_device):
    device_id, _ = registered_device
    # 3 successes, 1 failure → 75%
    for worked in [True, True, True, False]:
        client.post("/api/errors/sensor_disconnected/outcomes", headers=auth_headers, json={
            "device_id": device_id,
            "repair_action_id": 2,
            "worked": worked,
        })
    actions = client.get("/api/errors/sensor_disconnected", headers=auth_headers).json()["repair_actions"]
    action = next(a for a in actions if a["id"] == 2)
    assert action["success_rate"] == pytest.approx(0.75)


def test_record_outcome_without_action_id_still_succeeds(client, auth_headers, registered_device):
    device_id, _ = registered_device
    resp = client.post("/api/errors/sensor_disconnected/outcomes", headers=auth_headers, json={
        "device_id": device_id,
        "worked": True,
        "notes": "Fixed somehow",
    })
    assert resp.status_code == 201


def test_record_outcome_without_action_id_does_not_update_action_stats(client, auth_headers, registered_device):
    device_id, _ = registered_device
    client.post("/api/errors/sensor_disconnected/outcomes", headers=auth_headers, json={
        "device_id": device_id,
        "worked": True,
    })
    actions = client.get("/api/errors/sensor_disconnected", headers=auth_headers).json()["repair_actions"]
    for a in actions:
        assert a["occurrences"] == 0


def test_record_outcome_recorded_by_is_token_username(client, other_user_headers, registered_device):
    device_id, _ = registered_device
    resp = client.post("/api/errors/sensor_disconnected/outcomes", headers=other_user_headers, json={
        "device_id": device_id,
        "worked": True,
    })
    assert resp.json()["recorded_by"] == "alice"


def test_record_outcome_unknown_error_code_returns_404(client, auth_headers, registered_device):
    device_id, _ = registered_device
    resp = client.post("/api/errors/no_such_error/outcomes", headers=auth_headers, json={
        "device_id": device_id,
        "worked": True,
    })
    assert resp.status_code == 404


def test_record_outcome_only_updates_the_specified_action(client, auth_headers, registered_device):
    device_id, _ = registered_device
    # Record outcome against action id=1 only
    client.post("/api/errors/sensor_disconnected/outcomes", headers=auth_headers, json={
        "device_id": device_id,
        "repair_action_id": 1,
        "worked": True,
    })
    actions = client.get("/api/errors/sensor_disconnected", headers=auth_headers).json()["repair_actions"]
    untouched = [a for a in actions if a["id"] != 1]
    for a in untouched:
        assert a["occurrences"] == 0


# ─── POST /api/errors/{error_code}/actions ────────────────────────────────────


def test_add_repair_action_requires_auth(client):
    resp = client.post("/api/errors/sensor_disconnected/actions",
                       json={"action": "New step"})
    assert resp.status_code == 401


def test_add_repair_action_success(client, auth_headers):
    resp = client.post("/api/errors/sensor_disconnected/actions", headers=auth_headers, json={
        "action": "Replace sensor entirely",
        "description": "Swap out the sensor unit",
        "estimated_time_minutes": 20,
    })
    assert resp.status_code == 201
    data = resp.json()
    assert data["action"] == "Replace sensor entirely"
    assert data["description"] == "Swap out the sensor unit"
    assert data["estimated_time"] == 20
    assert data["step"] == 4  # sensor_disconnected already has 3 steps
    assert data["success_rate"] == 0.5
    assert data["occurrences"] == 0


def test_add_repair_action_step_auto_increments(client, auth_headers):
    for i in range(3):
        resp = client.post("/api/errors/photoeye_misaligned/actions", headers=auth_headers, json={
            "action": f"Extra step {i}",
        })
        assert resp.status_code == 201
        assert resp.json()["step"] == 3 + i  # photoeye already has 2 steps


def test_add_repair_action_appears_in_get(client, auth_headers):
    client.post("/api/errors/state_machine_stuck/actions", headers=auth_headers, json={
        "action": "Factory reset",
        "estimated_time_minutes": 30,
    })
    actions = client.get("/api/errors/state_machine_stuck", headers=auth_headers).json()["repair_actions"]
    assert any(a["action"] == "Factory reset" for a in actions)


def test_add_repair_action_to_unknown_error_returns_404(client, auth_headers):
    resp = client.post("/api/errors/no_such_error/actions", headers=auth_headers,
                       json={"action": "Won't work"})
    assert resp.status_code == 404


def test_add_repair_action_without_optional_fields(client, auth_headers):
    resp = client.post("/api/errors/internet_down/actions", headers=auth_headers,
                       json={"action": "Call ISP"})
    assert resp.status_code == 201
    data = resp.json()
    assert data["description"] is None
    assert data["estimated_time"] is None


def test_add_repair_action_missing_action_field_returns_422(client, auth_headers):
    resp = client.post("/api/errors/sensor_disconnected/actions", headers=auth_headers,
                       json={"description": "No action field"})
    assert resp.status_code == 422
