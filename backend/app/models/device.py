from datetime import datetime

from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text

from app.database import Base


class Device(Base):
    """Device model."""

    __tablename__ = "devices"

    id = Column(Integer, primary_key=True, index=True)
    device_id = Column(String(100), unique=True, nullable=False, index=True)
    api_key = Column(String(255), unique=True, nullable=False)
    device_type = Column(String(100))
    location = Column(String(255))
    customer_name = Column(String(255), index=True)
    online = Column(Boolean, default=False, index=True)
    online_since = Column(DateTime, nullable=True)
    last_seen = Column(DateTime)
    last_error = Column(String(255))
    last_error_timestamp = Column(DateTime)
    state = Column(String(100))
    firmware_version = Column(String(50))
    site_id = Column(Integer, ForeignKey("sites.id", ondelete="SET NULL"), nullable=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self) -> str:
        return f"<Device(id={self.id}, device_id={self.device_id}, online={self.online})>"


class DeviceErrorHistory(Base):
    """Device error history model."""

    __tablename__ = "device_error_history"

    id = Column(Integer, primary_key=True, index=True)
    device_id = Column(String(100), nullable=False, index=True)
    error_id = Column(Integer, ForeignKey("error_types.id"))
    error_message = Column(Text)
    occurred_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    resolved_at = Column(DateTime)
    resolution_notes = Column(Text)
    resolved_by = Column(String(100))

    def __repr__(self) -> str:
        return f"<DeviceErrorHistory(id={self.id}, device_id={self.device_id})>"


class MqttCredential(Base):
    """MQTT credentials model."""

    __tablename__ = "mqtt_credentials"

    id = Column(Integer, primary_key=True, index=True)
    device_id = Column(String(100), unique=True, nullable=False, index=True)
    username = Column(String(100), nullable=False)
    password_hash = Column(String(255), nullable=False)
    expires_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    def __repr__(self) -> str:
        return f"<MqttCredential(device_id={self.device_id})>"
