import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import and_, or_
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user, get_device_by_api_key
from app.models.device import Device, DeviceErrorHistory
from app.models.error import ErrorType, RepairAction
from app.models.organization import Organization, Site
from app.utils.security import hash_password

router = APIRouter(prefix="/api/devices", tags=["devices"])

UPTIME_WINDOW_DAYS = 30

# Maps sort_by name → Device column name, or None for Python-side sorts
VALID_SORT_FIELDS: dict[str, Optional[str]] = {
    "device_id": "device_id",
    "customer_name": "customer_name",
    "location": "location",
    "online": "online",
    "last_error": "last_error",
    "last_seen": "last_seen",
    "uptime_percent": None,  # computed in Python after DB fetch
}


# ─── Helpers ──────────────────────────────────────────────────────────────────


def _as_utc(dt: Optional[datetime]) -> Optional[datetime]:
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


def _compute_uptime(device_id: str, errors: list) -> float:
    """Uptime % over the last UPTIME_WINDOW_DAYS days from error history.

    Args:
        device_id: Device ID (used for validation only)
        errors: List of DeviceErrorHistory records already filtered to this device and time window
    """
    now = datetime.now(timezone.utc)
    window_start = now - timedelta(days=UPTIME_WINDOW_DAYS)
    window_seconds = UPTIME_WINDOW_DAYS * 24 * 3600

    # Clamp each error to the window boundary
    intervals = []
    for e in errors:
        start = max(_as_utc(e.occurred_at), window_start)
        end = _as_utc(e.resolved_at) if e.resolved_at else now
        if end > start:
            intervals.append((start, end))

    # Merge overlapping intervals so concurrent errors aren't double-counted
    intervals.sort(key=lambda x: x[0])
    merged: list[list] = []
    for start, end in intervals:
        if merged and start <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], end)
        else:
            merged.append([start, end])

    error_seconds = sum((e - s).total_seconds() for s, e in merged)
    return round(100.0 * (1 - error_seconds / window_seconds), 1)


def _get_troubleshooting(error_code: str, db: Session) -> Optional[dict]:
    """Return repair actions for an error code, sorted by step order."""
    error_type = db.query(ErrorType).filter(ErrorType.error_code == error_code).first()
    if not error_type:
        return None

    actions = (
        db.query(RepairAction)
        .filter(RepairAction.error_id == error_type.id)
        .order_by(RepairAction.step_order)
        .all()
    )
    if not actions:
        return None

    total_uses = sum(a.occurrences for a in actions if a.occurrences > 0) or 1
    total_successes = sum(a.successful_occurrences for a in actions)
    overall_rate = total_successes / total_uses

    return {
        "display_name": error_type.display_name,
        "success_rate": overall_rate,
        "repair_actions": [
            {
                "id": a.id,
                "step": a.step_order,
                "action": a.action,
                "description": a.description,
                "estimated_time": a.estimated_time_minutes,
                "success_rate": a.success_rate,
            }
            for a in actions
        ],
    }


# ─── Dashboard routes (JWT auth) ──────────────────────────────────────────────


@router.get("")
def list_devices(
    db: Session = Depends(get_db),
    _: str = Depends(get_current_user),
    # Filtering
    search: Optional[str] = Query(None, description="Search device_id, customer_name, location"),
    online: Optional[bool] = Query(None, description="Filter by online status"),
    customer: Optional[str] = Query(None, description="Filter by customer name"),
    has_error: Optional[bool] = Query(None, description="Filter by error presence"),
    # Sorting
    sort_by: str = Query("device_id", description=f"Sort field: {', '.join(sorted(VALID_SORT_FIELDS))}"),
    sort_order: str = Query("asc", description="Sort order: asc or desc"),
) -> dict:
    """List devices with filtering and sorting."""
    if sort_by not in VALID_SORT_FIELDS:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid sort_by '{sort_by}'. Valid fields: {sorted(VALID_SORT_FIELDS)}",
        )

    query = db.query(Device)

    # Apply filters
    if search:
        search_lower = f"%{search.lower()}%"
        query = query.filter(
            or_(
                Device.device_id.ilike(search_lower),
                Device.customer_name.ilike(search_lower),
                Device.location.ilike(search_lower),
            )
        )

    if online is not None:
        query = query.filter(Device.online == online)

    if customer:
        query = query.filter(Device.customer_name.ilike(f"%{customer.lower()}%"))

    if has_error is not None:
        if has_error:
            query = query.filter(Device.last_error.isnot(None))
        else:
            query = query.filter(Device.last_error.is_(None))

    # Apply DB-level sorting for column-based fields; uptime_percent is sorted in Python below
    db_sort_column = VALID_SORT_FIELDS[sort_by]
    if db_sort_column is not None:
        sort_field = getattr(Device, db_sort_column)
        if sort_order.lower() == "desc":
            query = query.order_by(sort_field.desc())
        else:
            query = query.order_by(sort_field)

    devices = query.all()

    # Fetch all error history in one query to avoid N+1
    now = datetime.now(timezone.utc)
    window_start = now - timedelta(days=UPTIME_WINDOW_DAYS)
    device_ids = [d.device_id for d in devices]

    error_history = (
        db.query(DeviceErrorHistory)
        .filter(
            DeviceErrorHistory.device_id.in_(device_ids),
            DeviceErrorHistory.occurred_at >= window_start,
        )
        .all()
    ) if device_ids else []

    # Group errors by device_id for O(1) lookup
    errors_by_device = {}
    for error in error_history:
        if error.device_id not in errors_by_device:
            errors_by_device[error.device_id] = []
        errors_by_device[error.device_id].append(error)

    # Fetch sites and orgs for devices that have site_id
    site_ids = {d.site_id for d in devices if d.site_id}
    sites_map: dict = {}
    orgs_map: dict = {}
    if site_ids:
        sites = db.query(Site).filter(Site.id.in_(site_ids)).all()
        org_ids = {s.organization_id for s in sites}
        orgs = db.query(Organization).filter(Organization.id.in_(org_ids)).all()
        orgs_map = {o.id: o for o in orgs}
        sites_map = {s.id: (s, orgs_map.get(s.organization_id)) for s in sites}

    device_list = [
        {
            "device_id": d.device_id,
            "customer_name": d.customer_name,
            "location": d.location,
            "online": d.online,
            "online_since": _as_utc(d.online_since).isoformat() if d.online_since else None,
            "last_seen": _as_utc(d.last_seen).isoformat() if d.last_seen else None,
            "last_error": d.last_error,
            "uptime_percent": _compute_uptime(d.device_id, errors_by_device.get(d.device_id, [])),
            "site_id": d.site_id,
            "site_nickname": sites_map[d.site_id][0].nickname if d.site_id and d.site_id in sites_map else None,
            "organization_id": sites_map[d.site_id][1].id if d.site_id and d.site_id in sites_map and sites_map[d.site_id][1] else None,
            "organization_name": sites_map[d.site_id][1].name if d.site_id and d.site_id in sites_map and sites_map[d.site_id][1] else None,
        }
        for d in devices
    ]

    if sort_by == "uptime_percent":
        device_list.sort(key=lambda d: d["uptime_percent"], reverse=(sort_order.lower() == "desc"))

    return {"devices": device_list}


@router.get("/{device_id}/status")
def device_status(
    device_id: str,
    db: Session = Depends(get_db),
    _: str = Depends(get_current_user),
) -> dict:
    """Full device status including last error detail and troubleshooting suggestions."""
    device = db.query(Device).filter(Device.device_id == device_id).first()
    if not device:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Device not found")

    last_error_detail = None
    if device.last_error:
        open_error = (
            db.query(DeviceErrorHistory)
            .filter(
                DeviceErrorHistory.device_id == device_id,
                DeviceErrorHistory.resolved_at.is_(None),
            )
            .order_by(DeviceErrorHistory.occurred_at.desc())
            .first()
        )
        occurred_at = (
            _as_utc(open_error.occurred_at).isoformat()
            if open_error
            else (_as_utc(device.last_error_timestamp).isoformat() if device.last_error_timestamp else None)
        )
        last_error_detail = {
            "code": device.last_error,
            "message": open_error.error_message if open_error else device.last_error,
            "occurred_at": occurred_at,
        }

    site = db.query(Site).filter(Site.id == device.site_id).first() if device.site_id else None
    org = db.query(Organization).filter(Organization.id == site.organization_id).first() if site else None

    return {
        "device_id": device.device_id,
        "online": device.online,
        "online_since": _as_utc(device.online_since).isoformat() if device.online_since else None,
        "last_seen": _as_utc(device.last_seen).isoformat() if device.last_seen else None,
        "state": device.state,
        "firmware_version": device.firmware_version,
        "location": device.location,
        "customer_name": device.customer_name,
        "device_type": device.device_type,
        "last_error": last_error_detail,
        "troubleshooting": _get_troubleshooting(device.last_error, db) if device.last_error else None,
        "site_id": device.site_id,
        "site_nickname": site.nickname if site else None,
        "organization_id": org.id if org else None,
        "organization_name": org.name if org else None,
    }


# ─── Device-facing routes (API key auth) ─────────────────────────────────────


class RegisterRequest(BaseModel):
    device_id: str
    device_type: Optional[str] = None
    location: Optional[str] = None
    customer_name: Optional[str] = None
    firmware_version: Optional[str] = None


class RegisterResponse(BaseModel):
    device_id: str
    api_key: str


@router.post("/register", response_model=RegisterResponse, status_code=status.HTTP_201_CREATED)
def register_device(body: RegisterRequest, db: Session = Depends(get_db)) -> RegisterResponse:
    """Auto-register a new device. Returns the plaintext API key — shown once.

    In DEBUG mode, re-registering an existing device rotates its API key and returns 200,
    allowing mock devices to restart cleanly without a database wipe.
    """
    from app.config import settings
    existing = db.query(Device).filter(Device.device_id == body.device_id).first()
    if existing:
        if not settings.DEBUG:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Device '{body.device_id}' is already registered",
            )
        # DEBUG: rotate API key so device can restart without a DB wipe
        api_key = secrets.token_urlsafe(32)
        existing.api_key = hash_password(api_key)
        db.commit()
        from fastapi.responses import JSONResponse
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={"device_id": existing.device_id, "api_key": api_key},
        )

    api_key = secrets.token_urlsafe(32)
    device = Device(
        device_id=body.device_id,
        api_key=hash_password(api_key),
        device_type=body.device_type,
        location=body.location,
        customer_name=body.customer_name,
        firmware_version=body.firmware_version,
    )
    db.add(device)
    db.commit()
    return RegisterResponse(device_id=device.device_id, api_key=api_key)


class HeartbeatRequest(BaseModel):
    online: bool = True
    state: Optional[str] = None
    firmware_version: Optional[str] = None
    last_error: Optional[str] = None
    last_error_message: Optional[str] = None
    throughput: Optional[float] = None  # items/hour
    cycle_time: Optional[float] = None  # seconds
    error_rate: Optional[float] = None  # 0-1


@router.patch("/{device_id}/heartbeat")
def device_heartbeat(
    device_id: str,
    body: HeartbeatRequest,
    db: Session = Depends(get_db),
    device: Device = Depends(get_device_by_api_key),
) -> dict:
    """Device heartbeat — updates online status, state, error tracking, and stores telemetry metrics."""
    from app.services.influxdb_metrics import metrics_db

    now = datetime.now(timezone.utc)
    error_changed = device.last_error != body.last_error
    was_online = device.online

    device.online = body.online
    device.last_seen = now
    if body.online and not was_online:
        device.online_since = now
    elif not body.online:
        device.online_since = None
    if body.state is not None:
        device.state = body.state
    if body.firmware_version is not None:
        device.firmware_version = body.firmware_version

    if error_changed:
        # Close the previous open error if one exists
        if device.last_error:
            open_error = (
                db.query(DeviceErrorHistory)
                .filter(
                    DeviceErrorHistory.device_id == device_id,
                    DeviceErrorHistory.resolved_at.is_(None),
                )
                .first()
            )
            if open_error:
                open_error.resolved_at = now

        # Open a new error record
        if body.last_error:
            error_type = db.query(ErrorType).filter(ErrorType.error_code == body.last_error).first()
            db.add(
                DeviceErrorHistory(
                    device_id=device_id,
                    error_id=error_type.id if error_type else None,
                    error_message=body.last_error_message or body.last_error,
                    occurred_at=now,
                )
            )

        device.last_error = body.last_error
        device.last_error_timestamp = now if body.last_error else None

    # Store telemetry metrics if present
    if any([body.throughput is not None, body.cycle_time is not None, body.error_rate is not None]):
        metrics_db.store_metrics(
            device_id,
            throughput=body.throughput,
            cycle_time=body.cycle_time,
            error_rate=body.error_rate,
        )

    db.commit()
    return {"status": "ok", "last_seen": now.isoformat()}
