from typing import Optional

from fastapi import Depends, Header, HTTPException, status
from jose import JWTError
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.device import Device
from app.utils.security import decode_access_token, verify_password


def get_current_user(authorization: Optional[str] = Header(None)) -> str:
    """JWT auth for dashboard users. Returns the username (JWT sub claim)."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    token = authorization.split(" ", 1)[1]
    try:
        payload = decode_access_token(token)
        return payload["sub"]
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")


def get_device_by_api_key(
    device_id: str,
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db),
) -> Device:
    """API key auth for device-facing endpoints. Validates key against the device row."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing API key")
    api_key = authorization.split(" ", 1)[1]
    device = db.query(Device).filter(Device.device_id == device_id).first()
    if not device or not verify_password(api_key, device.api_key):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key")
    return device
