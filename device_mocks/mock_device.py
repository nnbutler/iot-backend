"""Mock device simulator for development and testing.

This script simulates a real IoT device (PLC) that:
- Registers with the backend
- Sends periodic heartbeats with metrics
- Publishes logs
- Receives and executes commands
- Can simulate errors and recovery
"""

import json
import logging
import random
import threading
import time
from datetime import datetime, timezone
from typing import Optional

import paho.mqtt.client as mqtt
import requests

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class MockDevice:
    """Simulates an IoT device."""

    def __init__(
        self,
        device_id: str,
        backend_url: str = "https://localhost:8443",
        mqtt_broker: str = "localhost",
        mqtt_port: int = 1883,
        customer_name: str = "Test Customer",
        location: str = "Test Lab",
        device_type: str = "plc",
    ):
        self.device_id = device_id
        self.backend_url = backend_url
        self.mqtt_broker = mqtt_broker
        self.mqtt_port = mqtt_port
        self.customer_name = customer_name
        self.location = location
        self.device_type = device_type

        self.api_key: Optional[str] = None
        self.mqtt_client: Optional[mqtt.Client] = None
        self.running = False

        # Simulated device state
        self.online = True
        self.state = "running"
        self.firmware_version = "1.2.3"
        self.last_error: Optional[str] = None
        self.throughput = 0.0
        self.cycle_time = 0.0
        self.error_rate = 0.0

    def register(self) -> bool:
        """Register device with backend, get API key."""
        try:
            url = f"{self.backend_url}/api/devices/register"
            payload = {
                "device_id": self.device_id,
                "customer_name": self.customer_name,
                "location": self.location,
                "device_type": self.device_type,
                "firmware_version": self.firmware_version,
            }

            logger.info(f"Registering device {self.device_id}...")
            response = requests.post(url, json=payload, verify=False)
            response.raise_for_status()

            data = response.json()
            self.api_key = data["api_key"]
            logger.info(f"✓ Device registered. API Key: {self.api_key[:20]}...")
            return True
        except Exception as e:
            logger.error(f"Failed to register device: {e}")
            return False

    def _on_mqtt_connect(self, client, userdata, flags, rc):
        """MQTT connection callback."""
        if rc == 0:
            logger.info(f"✓ Connected to MQTT broker")
            # Subscribe to command topic
            client.subscribe(f"devices/{self.device_id}/commands")
            logger.info(f"Subscribed to devices/{self.device_id}/commands")
        else:
            logger.error(f"MQTT connection failed with code {rc}")

    def _on_mqtt_message(self, client, userdata, msg):
        """MQTT message callback - receive commands."""
        try:
            topic = msg.topic
            if f"devices/{self.device_id}/commands" in topic:
                payload = json.loads(msg.payload.decode())
                self._handle_command(payload)
        except Exception as e:
            logger.error(f"Error handling MQTT message: {e}")

    def _on_mqtt_disconnect(self, client, userdata, rc):
        """MQTT disconnection callback."""
        if rc != 0:
            logger.warning(f"Unexpected MQTT disconnection with code {rc}")

    def connect_mqtt(self) -> bool:
        """Connect to MQTT broker."""
        try:
            logger.info(f"Connecting to MQTT broker at {self.mqtt_broker}:{self.mqtt_port}...")
            self.mqtt_client = mqtt.Client(client_id=f"{self.device_id}-client")
            self.mqtt_client.on_connect = self._on_mqtt_connect
            self.mqtt_client.on_message = self._on_mqtt_message
            self.mqtt_client.on_disconnect = self._on_mqtt_disconnect

            self.mqtt_client.connect(self.mqtt_broker, self.mqtt_port, keepalive=60)
            self.mqtt_client.loop_start()
            return True
        except Exception as e:
            logger.error(f"Failed to connect to MQTT: {e}")
            return False

    def _simulate_workload(self):
        """Simulate realistic device metrics."""
        # Base throughput 1000-2000 items/hour
        self.throughput = random.uniform(1000, 2000)
        # Cycle time 1-3 seconds
        self.cycle_time = random.uniform(1.0, 3.0)
        # Error rate 0-5% normally
        self.error_rate = random.uniform(0.0, 0.05)

    def _simulate_error(self):
        """Randomly simulate an error (5% chance)."""
        if random.random() < 0.05:  # 5% chance per heartbeat
            errors = [
                "sensor_disconnected",
                "state_machine_timeout",
                "calibration_needed",
                "temperature_high",
            ]
            self.last_error = random.choice(errors)
            self.error_rate = 0.5  # High error rate during error
            logger.warning(f"🚨 Simulated error: {self.last_error}")
        elif self.last_error and random.random() < 0.3:  # 30% chance to recover
            logger.info(f"✓ Recovered from {self.last_error}")
            self.last_error = None
            self.error_rate = 0.0

    def send_heartbeat(self) -> bool:
        """Send heartbeat with current metrics."""
        try:
            self._simulate_workload()
            self._simulate_error()

            payload = {
                "online": self.online,
                "state": self.state,
                "firmware_version": self.firmware_version,
                "last_error": self.last_error,
                "throughput": round(self.throughput, 2),
                "cycle_time": round(self.cycle_time, 2),
                "error_rate": round(self.error_rate, 4),
            }

            # Try REST endpoint first (simpler)
            try:
                url = f"{self.backend_url}/api/devices/{self.device_id}/heartbeat"
                headers = {"Authorization": f"Bearer {self.api_key}"}
                response = requests.patch(url, json=payload, headers=headers, verify=False, timeout=5)
                response.raise_for_status()
                return True
            except Exception:
                # Fall back to MQTT
                if self.mqtt_client:
                    topic = f"devices/{self.device_id}/heartbeat"
                    self.mqtt_client.publish(topic, json.dumps(payload), qos=1)
                    return True
                return False

        except Exception as e:
            logger.error(f"Failed to send heartbeat: {e}")
            return False

    def send_log(self, level: str = "INFO", message: str = "Device operating normally") -> bool:
        """Send a log message."""
        try:
            payload = {
                "level": level,
                "message": message,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

            if self.mqtt_client:
                topic = f"devices/{self.device_id}/logs"
                result = self.mqtt_client.publish(topic, json.dumps(payload), qos=1)
                logger.info(f"📝 Published log [{level}]: {message}")
                return True
            logger.warning("⚠️  MQTT not connected, cannot send log")
            return False
        except Exception as e:
            logger.error(f"Failed to send log: {e}", exc_info=True)
            return False

    def _handle_command(self, command: dict):
        """Handle command from backend."""
        try:
            command_id = command.get("id")
            command_type = command.get("command_type")
            args = command.get("args", {})

            logger.info(f"📨 Received command {command_id}: {command_type}")

            # Simulate command execution
            time.sleep(random.uniform(1, 3))  # Simulate work

            # Determine if execution succeeds (95% success rate)
            success = random.random() < 0.95

            if success:
                status = "success"
                result = f"Successfully executed {command_type}"
                logger.info(f"✓ Command {command_id} executed successfully")
            else:
                status = "failed"
                result = f"Failed to execute {command_type}: Device busy"
                logger.error(f"✗ Command {command_id} failed")

            # Report result back to backend
            self._report_command_result(command_id, status, result)

        except Exception as e:
            logger.error(f"Error handling command: {e}")

    def _report_command_result(self, command_id: int, status: str, result: str):
        """Report command execution result back to backend."""
        try:
            payload = {
                "status": status,
                "result": result,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

            if self.mqtt_client:
                topic = f"devices/{self.device_id}/command-result/{command_id}"
                self.mqtt_client.publish(topic, json.dumps(payload), qos=1)
                logger.debug(f"Published command result for {command_id}")
        except Exception as e:
            logger.error(f"Failed to report command result: {e}")

    def run(self, heartbeat_interval: int = 10):
        """Run the device simulator.

        Args:
            heartbeat_interval: Seconds between heartbeats (default 10)
        """
        logger.info(f"Starting mock device {self.device_id}...")

        # Register with backend
        if not self.register():
            logger.error("Failed to register, aborting")
            return

        # Connect to MQTT
        if not self.connect_mqtt():
            logger.error("Failed to connect to MQTT, aborting")
            return

        self.running = True

        # Send periodic heartbeats
        logger.info(f"Sending heartbeat every {heartbeat_interval}s. Press Ctrl+C to stop.")
        try:
            while self.running:
                if self.send_heartbeat():
                    logger.info(
                        f"💓 Heartbeat sent. "
                        f"throughput={self.throughput:.0f}, "
                        f"cycle_time={self.cycle_time:.2f}s, "
                        f"error_rate={self.error_rate:.2%}, "
                        f"error={self.last_error or 'none'}"
                    )

                    # Send a log (temporarily always for testing)
                    if self.send_log("INFO", "Device running normally"):
                        logger.info("📝 Log message sent")
                    else:
                        logger.warning("⚠️  Failed to send log")

                time.sleep(heartbeat_interval)
        except KeyboardInterrupt:
            logger.info("\nShutting down...")
        finally:
            self.running = False
            if self.mqtt_client:
                self.mqtt_client.loop_stop()
                self.mqtt_client.disconnect()
            logger.info("Device stopped")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Mock IoT device simulator")
    parser.add_argument("--device-id", default="mock-device-001", help="Device ID")
    parser.add_argument("--backend-url", default="https://localhost:8443", help="Backend URL")
    parser.add_argument("--mqtt-broker", default="localhost", help="MQTT broker host")
    parser.add_argument("--mqtt-port", type=int, default=1883, help="MQTT broker port")
    parser.add_argument("--customer", default="Mock Customer", help="Customer name")
    parser.add_argument("--location", default="Mock Lab", help="Device location")
    parser.add_argument("--heartbeat-interval", type=int, default=10, help="Heartbeat interval in seconds")
    parser.add_argument("--num-devices", type=int, default=1, help="Number of devices to spawn")

    args = parser.parse_args()

    # Create and run device(s)
    devices = []
    for i in range(args.num_devices):
        device_id = f"{args.device_id}-{i+1}" if args.num_devices > 1 else args.device_id
        device = MockDevice(
            device_id=device_id,
            backend_url=args.backend_url,
            mqtt_broker=args.mqtt_broker,
            mqtt_port=args.mqtt_port,
            customer_name=args.customer,
            location=args.location,
        )
        devices.append(device)

    if args.num_devices > 1:
        # Run multiple devices in separate threads
        threads = []
        for device in devices:
            thread = threading.Thread(target=device.run, args=(args.heartbeat_interval,))
            thread.daemon = True
            thread.start()
            threads.append(thread)
            time.sleep(0.5)  # Stagger startup

        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            logger.info("Stopping all devices...")
            for device in devices:
                device.running = False
            for thread in threads:
                thread.join(timeout=5)
    else:
        # Run single device
        device = devices[0]
        device.run(args.heartbeat_interval)
