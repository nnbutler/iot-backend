"""Organization CRUD endpoints."""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models.organization import Organization

router = APIRouter(prefix="/api/organizations", tags=["organizations"])


class OrgBody(BaseModel):
    name: str


@router.get("")
def list_organizations(
    db: Session = Depends(get_db),
    _: str = Depends(get_current_user),
) -> dict:
    orgs = db.query(Organization).order_by(Organization.name).all()
    return {
        "organizations": [
            {"id": o.id, "name": o.name, "created_at": o.created_at.isoformat()}
            for o in orgs
        ]
    }


@router.post("", status_code=status.HTTP_201_CREATED)
def create_organization(
    body: OrgBody,
    db: Session = Depends(get_db),
    _: str = Depends(get_current_user),
) -> dict:
    existing = db.query(Organization).filter(Organization.name == body.name).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Organization name already exists")
    org = Organization(name=body.name)
    db.add(org)
    db.commit()
    db.refresh(org)
    return {"id": org.id, "name": org.name, "created_at": org.created_at.isoformat()}


@router.get("/{org_id}")
def get_organization(
    org_id: int,
    db: Session = Depends(get_db),
    _: str = Depends(get_current_user),
) -> dict:
    org = db.query(Organization).filter(Organization.id == org_id).first()
    if not org:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found")
    return {"id": org.id, "name": org.name, "created_at": org.created_at.isoformat()}


@router.patch("/{org_id}")
def update_organization(
    org_id: int,
    body: OrgBody,
    db: Session = Depends(get_db),
    _: str = Depends(get_current_user),
) -> dict:
    org = db.query(Organization).filter(Organization.id == org_id).first()
    if not org:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found")
    conflict = db.query(Organization).filter(Organization.name == body.name, Organization.id != org_id).first()
    if conflict:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Organization name already exists")
    org.name = body.name
    db.commit()
    return {"id": org.id, "name": org.name, "created_at": org.created_at.isoformat()}


@router.delete("/{org_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_organization(
    org_id: int,
    db: Session = Depends(get_db),
    _: str = Depends(get_current_user),
) -> None:
    from app.models.organization import Site
    org = db.query(Organization).filter(Organization.id == org_id).first()
    if not org:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found")
    site_count = db.query(Site).filter(Site.organization_id == org_id).count()
    if site_count > 0:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot delete organization with {site_count} site(s). Remove sites first.",
        )
    db.delete(org)
    db.commit()
