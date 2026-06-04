from datetime import datetime

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey

from app.database import Base


class User(Base):
    """User model."""

    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=False)
    username = Column(String(100), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    email = Column(String(100))
    role = Column(String(50), default="support", nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self) -> str:
        return f"<User(id={self.id}, username={self.username}, role={self.role})>"
