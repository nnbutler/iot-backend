"""Telemetry metrics endpoints."""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models.device import Device
from app.services.influxdb_metrics import metrics_db

router = APIRouter(prefix="/api/devices", tags=["metrics"])


@router.get("/{device_id}/metrics")
def get_device_metrics(
    device_id: str,
    db: Session = Depends(get_db),
    _: str = Depends(get_current_user),
    hours: int = Query(24, ge=1, le=720, description="Hours of historical data"),
) -> dict:
    """Get device telemetry metrics."""
    # Verify device exists
    device = db.query(Device).filter(Device.device_id == device_id).first()
    if not device:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Device not found")

    # Retrieve metrics from InfluxDB
    metrics = metrics_db.get_all_metrics(device_id, hours)

    return {
        "device_id": device_id,
        "hours": hours,
        "metrics": metrics,
        "latest": {
            "throughput": metrics_db.get_latest_metric(device_id, "throughput"),
            "cycle_time": metrics_db.get_latest_metric(device_id, "cycle_time"),
            "error_rate": metrics_db.get_latest_metric(device_id, "error_rate"),
        },
    }
