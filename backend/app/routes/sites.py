"""Site CRUD endpoints."""
import logging
from typing import Optional

import httpx
from timezonefinder import TimezoneFinder
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models.organization import Organization, Site, SiteComment
from app.models.device import Device

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/sites", tags=["sites"])


class SiteBody(BaseModel):
    organization_id: int
    nickname: str
    address: Optional[str] = None
    contact_name: Optional[str] = None
    contact_phone: Optional[str] = None
    contact_email: Optional[str] = None
    operating_hours: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    timezone: Optional[str] = None


class CommentBody(BaseModel):
    body: str


def _site_dict(site: Site, org_name: str) -> dict:
    return {
        "id": site.id,
        "organization_id": site.organization_id,
        "organization_name": org_name,
        "nickname": site.nickname,
        "address": site.address,
        "contact_name": site.contact_name,
        "contact_phone": site.contact_phone,
        "contact_email": site.contact_email,
        "operating_hours": site.operating_hours,
        "latitude": site.latitude,
        "longitude": site.longitude,
        "timezone": site.timezone,
        "created_at": site.created_at.isoformat(),
        "updated_at": site.updated_at.isoformat() if site.updated_at else None,
    }


@router.get("")
def list_sites(
    db: Session = Depends(get_db),
    _: str = Depends(get_current_user),
) -> dict:
    sites = db.query(Site).order_by(Site.nickname).all()
    org_ids = {s.organization_id for s in sites}
    orgs = {o.id: o.name for o in db.query(Organization).filter(Organization.id.in_(org_ids)).all()}
    return {"sites": [_site_dict(s, orgs.get(s.organization_id, "")) for s in sites]}


@router.post("", status_code=status.HTTP_201_CREATED)
def create_site(
    body: SiteBody,
    db: Session = Depends(get_db),
    _: str = Depends(get_current_user),
) -> dict:
    org = db.query(Organization).filter(Organization.id == body.organization_id).first()
    if not org:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found")
    site = Site(
        organization_id=body.organization_id,
        nickname=body.nickname,
        address=body.address,
        contact_name=body.contact_name,
        contact_phone=body.contact_phone,
        contact_email=body.contact_email,
        operating_hours=body.operating_hours,
        latitude=body.latitude,
        longitude=body.longitude,
        timezone=body.timezone,
    )
    db.add(site)
    db.commit()
    db.refresh(site)
    return _site_dict(site, org.name)


@router.get("/{site_id}")
def get_site(
    site_id: int,
    db: Session = Depends(get_db),
    _: str = Depends(get_current_user),
) -> dict:
    site = db.query(Site).filter(Site.id == site_id).first()
    if not site:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Site not found")
    org = db.query(Organization).filter(Organization.id == site.organization_id).first()
    devices = db.query(Device).filter(Device.site_id == site_id).all()
    result = _site_dict(site, org.name if org else "")
    result["devices"] = [
        {"device_id": d.device_id, "online": d.online, "last_error": d.last_error}
        for d in devices
    ]
    return result


@router.patch("/{site_id}")
def update_site(
    site_id: int,
    body: SiteBody,
    db: Session = Depends(get_db),
    _: str = Depends(get_current_user),
) -> dict:
    site = db.query(Site).filter(Site.id == site_id).first()
    if not site:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Site not found")
    org = db.query(Organization).filter(Organization.id == body.organization_id).first()
    if not org:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found")
    site.organization_id = body.organization_id
    site.nickname = body.nickname
    site.address = body.address
    site.contact_name = body.contact_name
    site.contact_phone = body.contact_phone
    site.contact_email = body.contact_email
    site.operating_hours = body.operating_hours
    # Only overwrite geo fields when explicitly provided; omitting them preserves existing geocoded data
    if "latitude" in body.model_fields_set:
        site.latitude = body.latitude
    if "longitude" in body.model_fields_set:
        site.longitude = body.longitude
    if "timezone" in body.model_fields_set:
        site.timezone = body.timezone
    db.commit()
    return _site_dict(site, org.name)


@router.delete("/{site_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_site(
    site_id: int,
    db: Session = Depends(get_db),
    _: str = Depends(get_current_user),
) -> None:
    site = db.query(Site).filter(Site.id == site_id).first()
    if not site:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Site not found")
    db.delete(site)
    db.commit()


@router.post("/{site_id}/geocode")
async def geocode_site(
    site_id: int,
    db: Session = Depends(get_db),
    _: str = Depends(get_current_user),
) -> dict:
    """Look up lat/lon and timezone from the site's address using Nominatim."""
    site = db.query(Site).filter(Site.id == site_id).first()
    if not site:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Site not found")
    if not site.address:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Site has no address to geocode")

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(
                "https://nominatim.openstreetmap.org/search",
                params={"q": site.address, "format": "json", "limit": 1},
                headers={"User-Agent": "iot-device-manager/1.0"},
            )
            resp.raise_for_status()
            results = resp.json()
    except Exception as e:
        logger.error(f"Nominatim request failed: {e}")
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Geocoding service unavailable")

    if not results:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Address not found")

    lat = float(results[0]["lat"])
    lon = float(results[0]["lon"])

    try:
        tz = TimezoneFinder().timezone_at(lat=lat, lng=lon) or "UTC"
    except Exception:
        tz = "UTC"

    site.latitude = lat
    site.longitude = lon
    site.timezone = tz
    db.commit()

    return {"latitude": lat, "longitude": lon, "timezone": tz}


# ── Comments ──────────────────────────────────────────────────────────────────

@router.get("/{site_id}/comments")
def list_comments(
    site_id: int,
    db: Session = Depends(get_db),
    _: str = Depends(get_current_user),
) -> dict:
    site = db.query(Site).filter(Site.id == site_id).first()
    if not site:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Site not found")
    comments = (
        db.query(SiteComment)
        .filter(SiteComment.site_id == site_id)
        .order_by(SiteComment.created_at.desc())
        .all()
    )
    return {
        "comments": [
            {"id": c.id, "username": c.username, "body": c.body, "created_at": c.created_at.isoformat()}
            for c in comments
        ]
    }


@router.post("/{site_id}/comments", status_code=status.HTTP_201_CREATED)
def add_comment(
    site_id: int,
    body: CommentBody,
    db: Session = Depends(get_db),
    username: str = Depends(get_current_user),
) -> dict:
    site = db.query(Site).filter(Site.id == site_id).first()
    if not site:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Site not found")
    if not body.body.strip():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Comment cannot be empty")
    comment = SiteComment(site_id=site_id, username=username, body=body.body.strip())
    db.add(comment)
    db.commit()
    db.refresh(comment)
    return {"id": comment.id, "username": comment.username, "body": comment.body, "created_at": comment.created_at.isoformat()}


@router.delete("/{site_id}/comments/{comment_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_comment(
    site_id: int,
    comment_id: int,
    db: Session = Depends(get_db),
    username: str = Depends(get_current_user),
) -> None:
    comment = db.query(SiteComment).filter(
        SiteComment.id == comment_id,
        SiteComment.site_id == site_id,
    ).first()
    if not comment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Comment not found")
    if comment.username != username:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot delete another user's comment")
    db.delete(comment)
    db.commit()


# ── Device assignment ─────────────────────────────────────────────────────────

@router.patch("/{site_id}/devices/{device_id}")
def assign_device_to_site(
    site_id: int,
    device_id: str,
    db: Session = Depends(get_db),
    _: str = Depends(get_current_user),
) -> dict:
    site = db.query(Site).filter(Site.id == site_id).first()
    if not site:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Site not found")
    device = db.query(Device).filter(Device.device_id == device_id).first()
    if not device:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Device not found")
    device.site_id = site_id
    db.commit()
    return {"device_id": device_id, "site_id": site_id}


@router.delete("/{site_id}/devices/{device_id}", status_code=status.HTTP_204_NO_CONTENT)
def unassign_device_from_site(
    site_id: int,
    device_id: str,
    db: Session = Depends(get_db),
    _: str = Depends(get_current_user),
) -> None:
    device = db.query(Device).filter(Device.device_id == device_id, Device.site_id == site_id).first()
    if not device:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Device not assigned to this site")
    device.site_id = None
    db.commit()
