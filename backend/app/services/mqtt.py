"""MQTT service for device-to-backend communication."""
import asyncio
import json
import logging
from typing import Optional

import paho.mqtt.client as mqtt
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import settings
from app.database import Base
from app.models.command import Command
from app.models.device import Device, DeviceErrorHistory
from app.models.error import ErrorType
from app.services.influxdb_metrics import metrics_db

logger = logging.getLogger(__name__)

MQTT_BROKER = "mosquitto"
MQTT_PORT = 1883
MQTT_TIMEOUT = 5


class MQTTManager:
    """Manages MQTT connections and message handling."""

    def __init__(self):
        self.client: Optional[mqtt.Client] = None
        self.connected = False
        self.db_session_factory: Optional[sessionmaker] = None
        self._loop: Optional[asyncio.AbstractEventLoop] = None

    def set_event_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        """Store the running asyncio loop so MQTT thread can schedule broadcasts."""
        self._loop = loop

    def _get_db(self) -> Session:
        """Get a database session for message processing."""
        if not self.db_session_factory:
            engine = create_engine(settings.DATABASE_URL)
            Base.metadata.create_all(bind=engine)
            self.db_session_factory = sessionmaker(bind=engine)
        return self.db_session_factory()

    def connect(self):
        """Connect to the MQTT broker."""
        try:
            self.client = mqtt.Client(client_id="device-manager-backend", protocol=mqtt.MQTTv311)
            self.client.on_connect = self._on_connect
            self.client.on_message = self._on_message
            self.client.on_disconnect = self._on_disconnect
            self.client.connect(MQTT_BROKER, MQTT_PORT, keepalive=60)
            self.client.loop_start()
            logger.info(f"MQTT connecting to {MQTT_BROKER}:{MQTT_PORT}")
        except Exception as e:
            logger.error(f"Failed to connect to MQTT broker: {e}")

    def disconnect(self):
        """Disconnect from the MQTT broker."""
        if self.client:
            self.client.loop_stop()
            self.client.disconnect()
            logger.info("MQTT disconnected")

    def _on_connect(self, client, userdata, flags, rc):
        """Handle MQTT connection."""
        if rc == 0:
            self.connected = True
            logger.info("MQTT connected successfully")
            # Subscribe to all device topics for debug visibility; logs stored by Telegraf
            client.subscribe("devices/+/heartbeat")
            client.subscribe("devices/+/command-result/+")
            client.subscribe("devices/+/logs")
        else:
            logger.error(f"MQTT connection failed with code {rc}")

    def _on_disconnect(self, client, userdata, rc):
        """Handle MQTT disconnection."""
        self.connected = False
        if rc != 0:
            logger.warning(f"Unexpected MQTT disconnection with code {rc}")
        else:
            logger.info("MQTT disconnected")

    def _on_message(self, client, userdata, msg):
        """Handle incoming MQTT messages."""
        try:
            # Broadcast raw message to any connected debug WebSocket clients
            if self._loop and self._loop.is_running():
                from app.routes.debug import broadcast
                payload_str = msg.payload.decode(errors="replace")
                asyncio.run_coroutine_threadsafe(
                    broadcast(msg.topic, payload_str), self._loop
                )

            topic_parts = msg.topic.split("/")
            if len(topic_parts) < 3:
                logger.warning(f"Invalid topic format: {msg.topic}")
                return

            device_id = topic_parts[1]
            message_type = topic_parts[2]

            if message_type == "heartbeat":
                self._handle_heartbeat(device_id, msg.payload)
            elif message_type == "command-result":
                command_id = topic_parts[3] if len(topic_parts) > 3 else None
                if command_id:
                    self._handle_command_result(device_id, command_id, msg.payload)
        except Exception as e:
            logger.error(f"Error handling MQTT message on {msg.topic}: {e}")

    def _handle_heartbeat(self, device_id: str, payload: bytes):
        """Process device heartbeat."""
        try:
            data = json.loads(payload.decode())
            db = self._get_db()
            try:
                device = db.query(Device).filter(Device.device_id == device_id).first()
                if not device:
                    logger.warning(f"Received heartbeat from unknown device: {device_id}")
                    return

                # Update device status
                from datetime import datetime, timezone

                now = datetime.now(timezone.utc)

                online = data.get("online", True)
                state = data.get("state")
                firmware = data.get("firmware_version")
                last_error = data.get("last_error")
                last_error_msg = data.get("last_error_message")

                # Store telemetry metrics if present (use explicit None checks to allow 0.0 values)
                throughput = data.get("throughput")
                cycle_time = data.get("cycle_time")
                error_rate = data.get("error_rate")
                if any(v is not None for v in [throughput, cycle_time, error_rate]):
                    metrics_db.store_metrics(device_id, throughput, cycle_time, error_rate)

                error_changed = device.last_error != last_error

                device.online = online
                device.last_seen = now
                if state:
                    device.state = state
                if firmware:
                    device.firmware_version = firmware

                if error_changed:
                    # Close previous error
                    if device.last_error:
                        open_error = (
                            db.query(DeviceErrorHistory)
                            .filter(
                                DeviceErrorHistory.device_id == device_id,
                                DeviceErrorHistory.resolved_at.is_(None),
                            )
                            .first()
                        )
                        if open_error:
                            open_error.resolved_at = now

                    # Open new error
                    if last_error:
                        error_type = db.query(ErrorType).filter(ErrorType.error_code == last_error).first()
                        db.add(
                            DeviceErrorHistory(
                                device_id=device_id,
                                error_id=error_type.id if error_type else None,
                                error_message=last_error_msg or last_error,
                                occurred_at=now,
                            )
                        )

                    device.last_error = last_error
                    device.last_error_timestamp = now if last_error else None

                db.commit()
                logger.info(f"Heartbeat processed for {device_id}: online={online}, error={last_error}")
            finally:
                db.close()
        except json.JSONDecodeError:
            logger.error(f"Invalid JSON in heartbeat payload: {payload}")
        except Exception as e:
            logger.error(f"Error processing heartbeat for {device_id}: {e}")

    def _handle_command_result(self, device_id: str, command_id: str, payload: bytes):
        """Process command execution result from device."""
        try:
            data = json.loads(payload.decode())
            db = self._get_db()
            try:
                cmd = db.query(Command).filter(Command.id == int(command_id)).first()
                if not cmd or cmd.device_id != device_id:
                    logger.warning(f"Received result for unknown command: {command_id}")
                    return

                status = data.get("status", "success")
                result = data.get("result")
                error_message = data.get("error_message")

                if status not in ("executing", "success", "failed"):
                    logger.warning(f"Invalid status in command result: {status}")
                    return

                cmd.status = status
                if result:
                    cmd.result = result
                if error_message:
                    cmd.error_message = error_message

                if status in ("success", "failed"):
                    from datetime import datetime, timezone
                    cmd.executed_at = datetime.now(timezone.utc)

                db.commit()
                logger.info(f"Command {command_id} result processed: {status}")
            finally:
                db.close()
        except json.JSONDecodeError:
            logger.error(f"Invalid JSON in command result payload: {payload}")
        except Exception as e:
            logger.error(f"Error processing command result for {device_id}: {e}")

    def publish_command(self, device_id: str, command_id: int, command_type: str, args: dict = None):
        """Publish a command to a device."""
        if not self.connected:
            logger.warning(f"MQTT not connected, cannot publish command to {device_id}")
            return False

        try:
            payload = {
                "id": command_id,
                "command_type": command_type,
                "args": args or {},
            }
            topic = f"devices/{device_id}/commands"
            result = self.client.publish(topic, json.dumps(payload), qos=1)
            if result.rc == mqtt.MQTT_ERR_SUCCESS:
                logger.info(f"Command {command_id} published to {topic}")
                return True
            else:
                logger.error(f"Failed to publish command {command_id}: {result.rc}")
                return False
        except Exception as e:
            logger.error(f"Error publishing command to {device_id}: {e}")
            return False


# Global MQTT manager instance
mqtt_manager = MQTTManager()
