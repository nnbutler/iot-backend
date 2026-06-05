#!/usr/bin/env python3
"""Test MQTT integration end-to-end."""
import json
import time

import paho.mqtt.client as mqtt

MQTT_BROKER = "localhost"
MQTT_PORT = 1883


def register_device():
    """Register a device via REST API."""
    import requests
    resp = requests.post("http://localhost:8080/api/devices/register", json={
        "device_id": "test-plc-001",
        "device_type": "plc",
        "location": "Test Lab",
        "customer_name": "Test Co",
        "firmware_version": "1.0.0",
    })
    if resp.status_code == 201:
        print(f"✓ Device registered: test-plc-001")
        return True
    elif resp.status_code == 409:
        print(f"✓ Device already registered: test-plc-001")
        return True
    else:
        print(f"✗ Failed to register device: {resp.status_code}")
        return False


def test_heartbeat_publish():
    """Simulate a device publishing a heartbeat."""
    print("\n=== Testing Device Heartbeat ===")
    client = mqtt.Client(client_id="test-device", protocol=mqtt.MQTTv311)
    client.connect(MQTT_BROKER, MQTT_PORT, keepalive=60)

    device_id = "test-plc-001"
    heartbeat = {
        "online": True,
        "state": "running",
        "firmware_version": "2.1.0",
        "last_error": None,
    }

    topic = f"devices/{device_id}/heartbeat"
    result = client.publish(topic, json.dumps(heartbeat), qos=1)
    print(f"Published heartbeat to {topic}: {result.rc}")

    client.disconnect()
    time.sleep(1)
    return True


def test_log_publish():
    """Simulate a device publishing logs."""
    print("\n=== Testing Device Logs ===")
    client = mqtt.Client(client_id="test-device-logs", protocol=mqtt.MQTTv311)
    client.connect(MQTT_BROKER, MQTT_PORT, keepalive=60)

    device_id = "test-plc-001"
    log = {
        "level": "WARNING",
        "message": "Sensor reading unstable",
    }

    topic = f"devices/{device_id}/logs"
    result = client.publish(topic, json.dumps(log), qos=1)
    print(f"Published log to {topic}: {result.rc}")

    client.disconnect()
    time.sleep(1)
    return True


def test_command_result_publish():
    """Simulate a device publishing a command result."""
    print("\n=== Testing Command Result ===")
    client = mqtt.Client(client_id="test-device-result", protocol=mqtt.MQTTv311)
    client.connect(MQTT_BROKER, MQTT_PORT, keepalive=60)

    device_id = "test-plc-001"
    command_id = "123"
    result_data = {
        "status": "success",
        "result": "PLC restarted successfully",
    }

    topic = f"devices/{device_id}/command-result/{command_id}"
    result = client.publish(topic, json.dumps(result_data), qos=1)
    print(f"Published result to {topic}: {result.rc}")

    client.disconnect()
    time.sleep(1)
    return True


def verify_device_created():
    """Verify the device exists in the DB after heartbeat."""
    print("\n=== Verifying Device in Database ===")
    import requests

    token = requests.post("http://localhost:8080/api/auth/login", json={
        "username": "support",
        "password": "support123",
    }).json()["access_token"]

    # List devices
    resp = requests.get("http://localhost:8080/api/devices", headers={
        "Authorization": f"Bearer {token}"
    })
    devices = resp.json()["devices"]
    device = next((d for d in devices if d["device_id"] == "test-plc-001"), None)

    if device:
        print(f"✓ Device found: {device['device_id']}")
        print(f"  Status: {'online' if device['online'] else 'offline'}")
        print(f"  Last error: {device['last_error']}")
        return True
    else:
        print("✗ Device not found in database")
        return False


def test_command_via_rest_api():
    """Test sending a command via REST API - should publish to MQTT."""
    print("\n=== Testing Command via REST API ===")
    import requests

    token = requests.post("http://localhost:8080/api/auth/login", json={
        "username": "support",
        "password": "support123",
    }).json()["access_token"]

    # Send a command
    resp = requests.post(
        "http://localhost:8080/api/devices/test-plc-001/commands",
        headers={"Authorization": f"Bearer {token}"},
        json={"command_type": "restart_plc"},
    )

    if resp.status_code == 201:
        cmd = resp.json()
        print(f"✓ Command sent via REST API")
        print(f"  Command ID: {cmd['id']}")
        print(f"  Type: {cmd['command_type']}")
        print(f"  Status: {cmd['status']}")
        print(f"  (Command should be published to MQTT topic: devices/test-plc-001/commands)")
        return True
    else:
        print(f"✗ Failed to send command: {resp.status_code}")
        return False


def test_command_history():
    """Verify command appears in history."""
    print("\n=== Verifying Command History ===")
    import requests

    token = requests.post("http://localhost:8080/api/auth/login", json={
        "username": "support",
        "password": "support123",
    }).json()["access_token"]

    resp = requests.get(
        "http://localhost:8080/api/devices/test-plc-001/commands",
        headers={"Authorization": f"Bearer {token}"},
    )

    if resp.status_code == 200:
        commands = resp.json()["commands"]
        if commands:
            cmd = commands[0]  # Most recent first
            print(f"✓ Command found in history")
            print(f"  Type: {cmd['command_type']}")
            print(f"  Status: {cmd['status']}")
            print(f"  Sent by: {cmd['sent_by']}")
            return True
        else:
            print("✗ No commands in history")
            return False
    else:
        print(f"✗ Failed to get command history: {resp.status_code}")
        return False


if __name__ == "__main__":
    print("Starting MQTT integration tests...")
    print(f"MQTT Broker: {MQTT_BROKER}:{MQTT_PORT}")

    try:
        register_device()
        time.sleep(1)

        test_heartbeat_publish()
        test_log_publish()
        test_command_result_publish()

        # Give backend time to process messages
        time.sleep(2)

        verify_device_created()
        test_command_via_rest_api()

        # Give MQTT time to publish
        time.sleep(1)

        test_command_history()
        print("\n✓ All tests completed!")
    except Exception as e:
        print(f"\n✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
