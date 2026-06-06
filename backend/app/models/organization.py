from datetime import datetime

from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, Float

from app.database import Base


class Organization(Base):
    """Organization model."""

    __tablename__ = "organizations"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), unique=True, nullable=False, index=True)
    logo_url = Column(Text, nullable=True)
    website = Column(String(512), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self) -> str:
        return f"<Organization(id={self.id}, name={self.name})>"


class Site(Base):
    """A physical location belonging to an organization."""

    __tablename__ = "sites"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=False, index=True)
    nickname = Column(String(255), nullable=False)
    address = Column(Text)
    contact_name = Column(String(255))
    contact_phone = Column(String(50))
    contact_email = Column(String(255))
    operating_hours = Column(Text)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    timezone = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self) -> str:
        return f"<Site(id={self.id}, nickname={self.nickname})>"


class SiteComment(Base):
    """A user comment or note attached to a site."""

    __tablename__ = "site_comments"

    id = Column(Integer, primary_key=True, index=True)
    site_id = Column(Integer, ForeignKey("sites.id", ondelete="CASCADE"), nullable=False, index=True)
    username = Column(String(100), nullable=False)
    body = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    def __repr__(self) -> str:
        return f"<SiteComment(id={self.id}, site_id={self.site_id})>"
