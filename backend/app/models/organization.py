from datetime import datetime

from sqlalchemy import Column, Integer, String, DateTime

from app.database import Base


class Organization(Base):
    """Organization model."""

    __tablename__ = "organizations"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), unique=True, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self) -> str:
        return f"<Organization(id={self.id}, name={self.name})>"
