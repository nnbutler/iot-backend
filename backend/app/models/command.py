from datetime import datetime

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text

from app.database import Base


class Command(Base):
    """Command model."""

    __tablename__ = "commands"

    id = Column(Integer, primary_key=True, index=True)
    device_id = Column(String(100), ForeignKey("devices.device_id"), nullable=False)
    command_type = Column(String(100), nullable=False)
    status = Column(String(50), default="sent")
    result = Column(Text)
    error_message = Column(Text)
    sent_by = Column(String(100))
    sent_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    executed_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    def __repr__(self) -> str:
        return f"<Command(id={self.id}, device_id={self.device_id}, status={self.status})>"
