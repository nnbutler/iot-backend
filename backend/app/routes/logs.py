"""Device log endpoints."""
from typing import List, Optional

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
    level: List[str] = Query(default=[], description="Filter by severity (repeatable): DEBUG, INFO, WARNING, ERROR, CRITICAL"),
    start_timestamp: Optional[str] = Query(None, description="Start of time range (ISO 8601). Defaults to 24h ago."),
    end_timestamp: Optional[str] = Query(None, description="End of time range (ISO 8601). Defaults to now."),
    limit: int = Query(50, ge=1, le=200, description="Number of logs to return"),
    before_timestamp: Optional[str] = Query(None, description="Pagination cursor: return logs before this timestamp (ISO 8601)"),
) -> dict:
    """Return device logs, newest first, within an optional time range."""
    device = db.query(Device).filter(Device.device_id == device_id).first()
    if not device:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Device not found")

    levels = [l.upper() for l in level]
    invalid = [l for l in levels if l not in VALID_LEVELS]
    if invalid:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid level(s): {invalid}. Must be one of: {', '.join(sorted(VALID_LEVELS))}",
        )

    result = metrics_db.get_logs(device_id, levels or None, limit, before_timestamp, start_timestamp, end_timestamp)

    return {
        "device_id": device_id,
        "logs": result["logs"],
        "has_more": result["has_more"],
        "next_before_timestamp": result["next_before_timestamp"],
    }
