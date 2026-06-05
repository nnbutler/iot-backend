"""Tests for MQTT log handling."""
import json
import pytest
from unittest.mock import Mock, patch, MagicMock

from app.models.device import Device


@pytest.fixture
def mqtt_manager():
    """Create a mock MQTT manager for testing."""
    from app.services.mqtt import MQTTManager
    return MQTTManager()


@pytest.fixture
def device_in_db(db_session):
    """Create a test device in the database."""
    device = Device(
        device_id="test-device-001",
        api_key="test-api-key",
        customer_name="Test Co",
        location="Test Lab",
    )
    db_session.add(device)
    db_session.commit()
    return device


@patch("app.services.mqtt.metrics_db")
def test_handle_logs_stores_to_influxdb(mock_metrics_db, mqtt_manager, device_in_db, db_session):
    """Test that _handle_logs stores logs to InfluxDB."""
    # Patch get_db to return our test session
    with patch("app.services.mqtt.MQTTManager._get_db", return_value=db_session):
        payload = json.dumps({
            "level": "ERROR",
            "message": "Sensor disconnected"
        }).encode()

        mqtt_manager._handle_logs("test-device-001", payload)

        # Verify store_log was called with correct arguments
        mock_metrics_db.store_log.assert_called_once_with(
            "test-device-001", "ERROR", "Sensor disconnected"
        )


@patch("app.services.mqtt.metrics_db")
def test_handle_logs_default_level(mock_metrics_db, mqtt_manager, device_in_db, db_session):
    """Test that default level is INFO."""
    with patch("app.services.mqtt.MQTTManager._get_db", return_value=db_session):
        payload = json.dumps({
            "message": "Test message"
        }).encode()

        mqtt_manager._handle_logs("test-device-001", payload)

        # Verify default level is INFO
        mock_metrics_db.store_log.assert_called_once_with(
            "test-device-001", "INFO", "Test message"
        )


@patch("app.services.mqtt.metrics_db")
def test_handle_logs_default_message(mock_metrics_db, mqtt_manager, device_in_db, db_session):
    """Test that default message is empty string."""
    with patch("app.services.mqtt.MQTTManager._get_db", return_value=db_session):
        payload = json.dumps({
            "level": "DEBUG"
        }).encode()

        mqtt_manager._handle_logs("test-device-001", payload)

        mock_metrics_db.store_log.assert_called_once_with(
            "test-device-001", "DEBUG", ""
        )


@patch("app.services.mqtt.metrics_db")
def test_handle_logs_unknown_device(mock_metrics_db, mqtt_manager, db_session):
    """Test that logs from unknown devices are rejected."""
    with patch("app.services.mqtt.MQTTManager._get_db", return_value=db_session):
        payload = json.dumps({
            "level": "ERROR",
            "message": "Test"
        }).encode()

        mqtt_manager._handle_logs("unknown-device", payload)

        # Should NOT call store_log for unknown device
        mock_metrics_db.store_log.assert_not_called()


@patch("app.services.mqtt.metrics_db")
def test_handle_logs_invalid_json(mock_metrics_db, mqtt_manager, device_in_db, db_session):
    """Test that invalid JSON is handled gracefully."""
    with patch("app.services.mqtt.MQTTManager._get_db", return_value=db_session):
        payload = b"not valid json"

        # Should not raise
        mqtt_manager._handle_logs("test-device-001", payload)

        # Should NOT call store_log
        mock_metrics_db.store_log.assert_not_called()


@patch("app.services.mqtt.metrics_db")
def test_handle_logs_influxdb_error(mock_metrics_db, mqtt_manager, device_in_db, db_session):
    """Test that InfluxDB errors are handled gracefully."""
    mock_metrics_db.store_log.side_effect = Exception("InfluxDB write failed")

    with patch("app.services.mqtt.MQTTManager._get_db", return_value=db_session):
        payload = json.dumps({
            "level": "ERROR",
            "message": "Test"
        }).encode()

        # Should not raise
        mqtt_manager._handle_logs("test-device-001", payload)
