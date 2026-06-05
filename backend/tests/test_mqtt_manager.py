"""Tests for MQTT message handling and device communication."""
import json
from datetime import datetime, timezone
from unittest.mock import MagicMock, Mock, patch

import pytest

from app.models.command import Command
from app.models.device import Device, DeviceErrorHistory, DeviceLog
from app.models.error import ErrorType
from app.services.mqtt import MQTTManager


@pytest.fixture
def mqtt_manager():
    """Create an MQTT manager instance without connecting."""
    manager = MQTTManager()
    # Don't actually connect to broker
    return manager


@pytest.fixture
def mock_client(mqtt_manager):
    """Create a mock MQTT client."""
    with patch("app.services.mqtt.mqtt.Client") as mock_client_class:
        mock = MagicMock()
        mock_client_class.return_value = mock
        mqtt_manager.client = mock
        mqtt_manager.connected = True
        yield mock


@pytest.fixture
def mock_db_session():
    """Create a mock database session."""
    return MagicMock()


@pytest.fixture
def registered_device(db_session):
    """Create a test device in the database."""
    device = Device(
        device_id="mqtt-test-01",
        api_key="hashed-key-1234",
        device_type="plc",
        location="Test Lab",
        customer_name="Test Co",
        firmware_version="1.0.0",
    )
    db_session.add(device)
    db_session.commit()
    db_session.refresh(device)
    return device


@pytest.fixture
def registered_error_type(db_session):
    """Create a test error type in the database."""
    error = ErrorType(
        error_code="test_error",
        display_name="Test Error",
        severity="medium",
    )
    db_session.add(error)
    db_session.commit()
    db_session.refresh(error)
    return error


# ─── Connection Tests ─────────────────────────────────────────────────────────


def test_mqtt_manager_connect(mqtt_manager):
    """Test MQTT manager connects to broker."""
    with patch("app.services.mqtt.mqtt.Client") as mock_client_class:
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        mqtt_manager.connect()

        assert mqtt_manager.client is not None
        mock_client.connect.assert_called_once_with("mosquitto", 1883, keepalive=60)
        mock_client.loop_start.assert_called_once()


def test_mqtt_manager_disconnect(mqtt_manager):
    """Test MQTT manager disconnects from broker."""
    mqtt_manager.client = MagicMock()
    mqtt_manager.disconnect()

    mqtt_manager.client.loop_stop.assert_called_once()
    mqtt_manager.client.disconnect.assert_called_once()


def test_on_connect_handler(mqtt_manager):
    """Test successful connection handler subscribes to topics."""
    mqtt_manager.client = MagicMock()
    mqtt_manager._on_connect(mqtt_manager.client, None, {}, 0)

    assert mqtt_manager.connected is True
    mqtt_manager.client.subscribe.assert_any_call("devices/+/heartbeat")
    mqtt_manager.client.subscribe.assert_any_call("devices/+/logs")
    mqtt_manager.client.subscribe.assert_any_call("devices/+/command-result/+")


def test_on_connect_handler_failure(mqtt_manager):
    """Test connection failure sets connected to False."""
    mqtt_manager.client = MagicMock()
    mqtt_manager._on_connect(mqtt_manager.client, None, {}, 1)

    assert mqtt_manager.connected is False


def test_on_disconnect_handler(mqtt_manager):
    """Test disconnection handler."""
    mqtt_manager.connected = True
    mqtt_manager._on_disconnect(mqtt_manager.client, None, 0)

    assert mqtt_manager.connected is False


# ─── Heartbeat Message Tests ──────────────────────────────────────────────────


def test_handle_heartbeat_updates_device(mqtt_manager, db_session, registered_device):
    """Test heartbeat updates device status."""
    mqtt_manager.db_session_factory = MagicMock()
    mqtt_manager.db_session_factory.return_value = db_session

    heartbeat = {
        "online": True,
        "state": "running",
        "firmware_version": "2.0.0",
    }

    mqtt_manager._handle_heartbeat("mqtt-test-01", json.dumps(heartbeat).encode())

    device = db_session.query(Device).filter(Device.device_id == "mqtt-test-01").first()
    assert device.online is True
    assert device.state == "running"
    assert device.firmware_version == "2.0.0"
    assert device.last_seen is not None


def test_handle_heartbeat_sets_error(mqtt_manager, db_session, registered_device, registered_error_type):
    """Test heartbeat with error opens error history."""
    mqtt_manager.db_session_factory = MagicMock()
    mqtt_manager.db_session_factory.return_value = db_session

    heartbeat = {
        "online": True,
        "last_error": "test_error",
        "last_error_message": "Something went wrong",
    }

    mqtt_manager._handle_heartbeat("mqtt-test-01", json.dumps(heartbeat).encode())

    db_session.expire_all()
    device = db_session.query(Device).filter(Device.device_id == "mqtt-test-01").first()
    assert device.last_error == "test_error"

    error_history = (
        db_session.query(DeviceErrorHistory)
        .filter(DeviceErrorHistory.device_id == "mqtt-test-01")
        .first()
    )
    assert error_history is not None
    assert error_history.error_message == "Something went wrong"
    assert error_history.resolved_at is None


def test_handle_heartbeat_clears_error(mqtt_manager, db_session, registered_device, registered_error_type):
    """Test heartbeat without error closes error history."""
    mqtt_manager.db_session_factory = MagicMock()
    mqtt_manager.db_session_factory.return_value = db_session

    # First set an error
    device = db_session.query(Device).filter(Device.device_id == "mqtt-test-01").first()
    device.last_error = "test_error"
    error = db_session.query(ErrorType).filter(ErrorType.error_code == "test_error").first()
    db_session.add(
        DeviceErrorHistory(
            device_id="mqtt-test-01",
            error_id=error.id if error else None,
            error_message="Test error",
            occurred_at=datetime.now(timezone.utc),
        )
    )
    db_session.commit()

    # Now send heartbeat with no error
    heartbeat = {"online": True}
    mqtt_manager._handle_heartbeat("mqtt-test-01", json.dumps(heartbeat).encode())

    db_session.expire_all()
    device = db_session.query(Device).filter(Device.device_id == "mqtt-test-01").first()
    assert device.last_error is None

    open_errors = (
        db_session.query(DeviceErrorHistory)
        .filter(
            DeviceErrorHistory.device_id == "mqtt-test-01",
            DeviceErrorHistory.resolved_at.is_(None),
        )
        .all()
    )
    assert len(open_errors) == 0


def test_handle_heartbeat_unknown_device_ignored(mqtt_manager, db_session):
    """Test heartbeat from unknown device is ignored."""
    mqtt_manager.db_session_factory = MagicMock()
    mqtt_manager.db_session_factory.return_value = db_session

    heartbeat = {"online": True}
    # Should not raise, just log warning
    mqtt_manager._handle_heartbeat("unknown-device", json.dumps(heartbeat).encode())


def test_handle_heartbeat_invalid_json(mqtt_manager, db_session):
    """Test heartbeat with invalid JSON is handled gracefully."""
    mqtt_manager.db_session_factory = MagicMock()
    mqtt_manager.db_session_factory.return_value = db_session

    # Should not raise
    mqtt_manager._handle_heartbeat("mqtt-test-01", b"not valid json")


def test_handle_heartbeat_partial_data(mqtt_manager, db_session, registered_device):
    """Test heartbeat with missing optional fields."""
    mqtt_manager.db_session_factory = MagicMock()
    mqtt_manager.db_session_factory.return_value = db_session

    heartbeat = {"online": False}  # Only online field
    mqtt_manager._handle_heartbeat("mqtt-test-01", json.dumps(heartbeat).encode())

    device = db_session.query(Device).filter(Device.device_id == "mqtt-test-01").first()
    assert device.online is False


# ─── Log Message Tests ────────────────────────────────────────────────────────


def test_handle_logs_creates_device_log(mqtt_manager, db_session, registered_device):
    """Test logs are stored in database."""
    mqtt_manager.db_session_factory = MagicMock()
    mqtt_manager.db_session_factory.return_value = db_session

    log = {
        "level": "WARNING",
        "message": "Sensor reading unstable",
    }

    mqtt_manager._handle_logs("mqtt-test-01", json.dumps(log).encode())

    db_session.expire_all()
    device_log = (
        db_session.query(DeviceLog)
        .filter(DeviceLog.device_id == "mqtt-test-01")
        .first()
    )
    assert device_log is not None
    assert device_log.level == "WARNING"
    assert device_log.message == "Sensor reading unstable"


def test_handle_logs_default_level(mqtt_manager, db_session, registered_device):
    """Test logs with missing level default to INFO."""
    mqtt_manager.db_session_factory = MagicMock()
    mqtt_manager.db_session_factory.return_value = db_session

    log = {"message": "Something happened"}
    mqtt_manager._handle_logs("mqtt-test-01", json.dumps(log).encode())

    db_session.expire_all()
    device_log = (
        db_session.query(DeviceLog)
        .filter(DeviceLog.device_id == "mqtt-test-01")
        .first()
    )
    assert device_log.level == "INFO"


def test_handle_logs_unknown_device_ignored(mqtt_manager, db_session):
    """Test logs from unknown device are ignored."""
    mqtt_manager.db_session_factory = MagicMock()
    mqtt_manager.db_session_factory.return_value = db_session

    log = {"level": "ERROR", "message": "Test"}
    # Should not raise
    mqtt_manager._handle_logs("unknown-device", json.dumps(log).encode())


def test_handle_logs_invalid_json(mqtt_manager, db_session):
    """Test logs with invalid JSON handled gracefully."""
    mqtt_manager.db_session_factory = MagicMock()
    mqtt_manager.db_session_factory.return_value = db_session

    # Should not raise
    mqtt_manager._handle_logs("mqtt-test-01", b"{invalid json")


# ─── Command Result Tests ─────────────────────────────────────────────────────


def test_handle_command_result_updates_status(mqtt_manager, db_session, registered_device):
    """Test command result updates command status."""
    mqtt_manager.db_session_factory = lambda: db_session

    # Create a command
    cmd = Command(
        device_id="mqtt-test-01",
        command_type="restart_plc",
        status="sent",
        sent_by="test",
    )
    db_session.add(cmd)
    db_session.commit()
    cmd_id = cmd.id

    result = {
        "status": "success",
        "result": "PLC restarted",
    }

    mqtt_manager._handle_command_result(
        "mqtt-test-01", str(cmd_id), json.dumps(result).encode()
    )

    db_session.expire_all()
    updated_cmd = db_session.query(Command).filter(Command.id == cmd_id).first()
    assert updated_cmd.status == "success"
    assert updated_cmd.result == "PLC restarted"
    assert updated_cmd.executed_at is not None


def test_handle_command_result_executing_no_executed_at(mqtt_manager, db_session, registered_device):
    """Test executing status doesn't set executed_at."""
    mqtt_manager.db_session_factory = lambda: db_session

    cmd = Command(
        device_id="mqtt-test-01",
        command_type="restart_plc",
        status="sent",
        sent_by="test",
    )
    db_session.add(cmd)
    db_session.commit()
    cmd_id = cmd.id

    result = {"status": "executing"}
    mqtt_manager._handle_command_result(
        "mqtt-test-01", str(cmd_id), json.dumps(result).encode()
    )

    db_session.expire_all()
    updated_cmd = db_session.query(Command).filter(Command.id == cmd_id).first()
    assert updated_cmd.status == "executing"
    assert updated_cmd.executed_at is None


def test_handle_command_result_failed(mqtt_manager, db_session, registered_device):
    """Test failed command result."""
    mqtt_manager.db_session_factory = lambda: db_session

    cmd = Command(
        device_id="mqtt-test-01",
        command_type="restart_plc",
        status="sent",
        sent_by="test",
    )
    db_session.add(cmd)
    db_session.commit()
    cmd_id = cmd.id

    result = {
        "status": "failed",
        "error_message": "Timeout",
    }

    mqtt_manager._handle_command_result(
        "mqtt-test-01", str(cmd_id), json.dumps(result).encode()
    )

    db_session.expire_all()
    updated_cmd = db_session.query(Command).filter(Command.id == cmd_id).first()
    assert updated_cmd.status == "failed"
    assert updated_cmd.error_message == "Timeout"
    assert updated_cmd.executed_at is not None


def test_handle_command_result_invalid_status(mqtt_manager, db_session, registered_device):
    """Test invalid status is rejected."""
    mqtt_manager.db_session_factory = MagicMock()
    mqtt_manager.db_session_factory.return_value = db_session

    cmd = Command(
        device_id="mqtt-test-01",
        command_type="restart_plc",
        status="sent",
        sent_by="test",
    )
    db_session.add(cmd)
    db_session.commit()
    db_session.refresh(cmd)

    result = {"status": "invalid_status"}
    mqtt_manager._handle_command_result(
        "mqtt-test-01", str(cmd.id), json.dumps(result).encode()
    )

    db_session.expire_all()
    updated_cmd = db_session.query(Command).filter(Command.id == cmd.id).first()
    # Status should not change
    assert updated_cmd.status == "sent"


def test_handle_command_result_unknown_command_ignored(mqtt_manager, db_session):
    """Test result from unknown command is ignored."""
    mqtt_manager.db_session_factory = MagicMock()
    mqtt_manager.db_session_factory.return_value = db_session

    result = {"status": "success"}
    # Should not raise
    mqtt_manager._handle_command_result(
        "mqtt-test-01", "999999", json.dumps(result).encode()
    )


def test_handle_command_result_invalid_json(mqtt_manager, db_session):
    """Test command result with invalid JSON handled gracefully."""
    mqtt_manager.db_session_factory = MagicMock()
    mqtt_manager.db_session_factory.return_value = db_session

    # Should not raise
    mqtt_manager._handle_command_result("mqtt-test-01", "123", b"bad json")


# ─── Message Routing Tests ────────────────────────────────────────────────────


def test_on_message_heartbeat_topic(mqtt_manager, db_session, registered_device):
    """Test on_message routes heartbeat messages."""
    mqtt_manager.db_session_factory = MagicMock()
    mqtt_manager.db_session_factory.return_value = db_session

    msg = MagicMock()
    msg.topic = "devices/mqtt-test-01/heartbeat"
    msg.payload = json.dumps({"online": True}).encode()

    mqtt_manager._on_message(mqtt_manager.client, None, msg)

    device = db_session.query(Device).filter(Device.device_id == "mqtt-test-01").first()
    assert device.online is True


def test_on_message_logs_topic(mqtt_manager, db_session, registered_device):
    """Test on_message routes log messages."""
    mqtt_manager.db_session_factory = MagicMock()
    mqtt_manager.db_session_factory.return_value = db_session

    msg = MagicMock()
    msg.topic = "devices/mqtt-test-01/logs"
    msg.payload = json.dumps({"level": "INFO", "message": "Test"}).encode()

    mqtt_manager._on_message(mqtt_manager.client, None, msg)

    log = db_session.query(DeviceLog).filter(DeviceLog.device_id == "mqtt-test-01").first()
    assert log is not None


def test_on_message_command_result_topic(mqtt_manager, db_session, registered_device):
    """Test on_message routes command result messages."""
    mqtt_manager.db_session_factory = lambda: db_session
    mqtt_manager.client = MagicMock()  # Ensure client is initialized

    cmd = Command(
        device_id="mqtt-test-01",
        command_type="restart_plc",
        status="sent",
        sent_by="test",
    )
    db_session.add(cmd)
    db_session.commit()
    cmd_id = cmd.id

    msg = MagicMock()
    msg.topic = f"devices/mqtt-test-01/command-result/{cmd_id}"
    msg.payload = json.dumps({"status": "success"}).encode()

    mqtt_manager._on_message(mqtt_manager.client, None, msg)

    db_session.expire_all()
    updated_cmd = db_session.query(Command).filter(Command.id == cmd_id).first()
    assert updated_cmd.status == "success"


def test_on_message_invalid_topic(mqtt_manager):
    """Test on_message handles invalid topic format."""
    msg = MagicMock()
    msg.topic = "invalid/topic/format"
    msg.payload = b"data"

    # Should not raise
    mqtt_manager._on_message(mqtt_manager.client, None, msg)


# ─── Command Publishing Tests ─────────────────────────────────────────────────


def test_publish_command_success(mqtt_manager, mock_client):
    """Test publishing a command to device."""
    mock_client.publish.return_value.rc = 0

    result = mqtt_manager.publish_command("mqtt-test-01", 42, "restart_plc")

    assert result is True
    mock_client.publish.assert_called_once()
    call_args = mock_client.publish.call_args
    assert call_args[0][0] == "devices/mqtt-test-01/commands"
    payload = json.loads(call_args[0][1])
    assert payload["id"] == 42
    assert payload["command_type"] == "restart_plc"


def test_publish_command_with_args(mqtt_manager, mock_client):
    """Test publishing command with arguments."""
    mock_client.publish.return_value.rc = 0

    result = mqtt_manager.publish_command(
        "mqtt-test-01", 42, "custom_cmd", args={"param": "value"}
    )

    assert result is True
    call_args = mock_client.publish.call_args
    payload = json.loads(call_args[0][1])
    assert payload["args"] == {"param": "value"}


def test_publish_command_not_connected(mqtt_manager):
    """Test publish fails gracefully when not connected."""
    mqtt_manager.connected = False

    result = mqtt_manager.publish_command("mqtt-test-01", 42, "restart_plc")

    assert result is False


def test_publish_command_mqtt_error(mqtt_manager, mock_client):
    """Test publish handles MQTT errors."""
    mock_client.publish.return_value.rc = 4  # MQTT_ERR_NO_CONN

    result = mqtt_manager.publish_command("mqtt-test-01", 42, "restart_plc")

    assert result is False


def test_publish_command_exception(mqtt_manager, mock_client):
    """Test publish handles exceptions gracefully."""
    mock_client.publish.side_effect = Exception("MQTT error")

    result = mqtt_manager.publish_command("mqtt-test-01", 42, "restart_plc")

    assert result is False
