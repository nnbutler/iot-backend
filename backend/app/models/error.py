from datetime import datetime

from sqlalchemy import Boolean, Column, Integer, String, DateTime, ForeignKey, Text, Float

from app.database import Base


class ErrorType(Base):
    """Error type model."""

    __tablename__ = "error_types"

    id = Column(Integer, primary_key=True, index=True)
    error_code = Column(String(100), unique=True, nullable=False, index=True)
    display_name = Column(String(255), nullable=False)
    description = Column(Text)
    severity = Column(String(20))
    customer_visible_message = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self) -> str:
        return f"<ErrorType(id={self.id}, error_code={self.error_code})>"


class RepairAction(Base):
    """Repair action model."""

    __tablename__ = "repair_actions"

    id = Column(Integer, primary_key=True, index=True)
    error_id = Column(Integer, ForeignKey("error_types.id"), nullable=False)
    step_order = Column(Integer, nullable=False)
    action = Column(Text, nullable=False)
    description = Column(Text)
    estimated_time_minutes = Column(Integer)
    success_rate = Column(Float, default=0.5)
    occurrences = Column(Integer, default=0)
    successful_occurrences = Column(Integer, default=0)
    created_by = Column(String(100))
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self) -> str:
        return f"<RepairAction(id={self.id}, error_id={self.error_id}, step={self.step_order})>"


class RepairOutcome(Base):
    """Repair outcome model."""

    __tablename__ = "repair_outcomes"

    id = Column(Integer, primary_key=True, index=True)
    device_id = Column(String(100), nullable=False)
    error_id = Column(Integer, ForeignKey("error_types.id"), nullable=False)
    repair_action_id = Column(Integer, ForeignKey("repair_actions.id"))
    worked = Column(Boolean, nullable=False)
    notes = Column(Text)
    time_spent_minutes = Column(Integer)
    attempted_by = Column(String(100))
    attempted_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    def __repr__(self) -> str:
        return f"<RepairOutcome(id={self.id}, device_id={self.device_id}, worked={self.worked})>"
