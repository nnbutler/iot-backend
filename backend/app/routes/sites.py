"""Site CRUD endpoints."""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models.organization import Organization, Site
from app.models.device import Device

router = APIRouter(prefix="/api/sites", tags=["sites"])


class SiteBody(BaseModel):
    organization_id: int
    nickname: str
    address: Optional[str] = None
    contact_name: Optional[str] = None
    contact_phone: Optional[str] = None
    contact_email: Optional[str] = None
    operating_hours: Optional[str] = None


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
    return {
        "sites": [_site_dict(s, orgs.get(s.organization_id, "")) for s in sites]
    }


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


@router.patch("/{site_id}/devices/{device_id}")
def assign_device_to_site(
    site_id: int,
    device_id: str,
    db: Session = Depends(get_db),
    _: str = Depends(get_current_user),
) -> dict:
    """Assign a device to a site."""
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
    """Remove a device from a site."""
    device = db.query(Device).filter(Device.device_id == device_id, Device.site_id == site_id).first()
    if not device:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Device not assigned to this site")
    device.site_id = None
    db.commit()
