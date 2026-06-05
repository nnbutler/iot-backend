"""Device log endpoints."""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models.device import Device
from app.services.influxdb_metrics import metrics_db

router = APIRouter(tags=["logs"])

VALID_LEVELS = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}


@router.get("/api/devices/{device_id}/logs")
def list_device_logs(
    device_id: str,
    db: Session = Depends(get_db),
    _: str = Depends(get_current_user),
    level: Optional[str] = Query(None, description="Filter by severity: DEBUG, INFO, WARNING, ERROR, CRITICAL"),
    limit: int = Query(50, ge=1, le=200, description="Number of logs to return"),
    before_timestamp: Optional[str] = Query(None, description="Return logs before this timestamp (cursor pagination, ISO 8601)"),
) -> dict:
    """Return device logs, newest first, with optional severity filtering."""
    device = db.query(Device).filter(Device.device_id == device_id).first()
    if not device:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Device not found")

    if level and level.upper() not in VALID_LEVELS:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid level '{level}'. Must be one of: {', '.join(sorted(VALID_LEVELS))}",
        )

    result = metrics_db.get_logs(device_id, level.upper() if level else None, limit, before_timestamp)

    return {
        "device_id": device_id,
        "logs": result["logs"],
        "has_more": result["has_more"],
        "next_before_timestamp": result["next_before_timestamp"],
    }
