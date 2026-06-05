from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Header, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models.command import Command
from app.models.device import Device
from app.utils.security import verify_password

router = APIRouter(tags=["commands"])

ALLOWED_COMMANDS = {"restart_plc", "reset_state_machine", "reboot_device", "clear_error_log"}

COMMAND_LABELS = {
    "restart_plc": "Restart PLC",
    "reset_state_machine": "Reset State Machine",
    "reboot_device": "Reboot Device",
    "clear_error_log": "Clear Error Log",
}


# ─── Device auth for command result updates ───────────────────────────────────


def _get_device_for_command(
    command_id: int,
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db),
) -> Device:
    """Verify the API key matches the device that owns this command."""
    command = db.query(Command).filter(Command.id == command_id).first()
    if not command:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Command not found")
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing API key")
    api_key = authorization.split(" ", 1)[1]
    device = db.query(Device).filter(Device.device_id == command.device_id).first()
    if not device or not verify_password(api_key, device.api_key):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key")
    return device


# ─── Routes ───────────────────────────────────────────────────────────────────


@router.get("/api/commands/available")
def list_available_commands(_: str = Depends(get_current_user)) -> dict:
    """Return the list of commands that can be sent to devices."""
    return {
        "commands": [
            {"command_type": k, "label": v}
            for k, v in COMMAND_LABELS.items()
        ]
    }


class SendCommandRequest(BaseModel):
    command_type: str


@router.post("/api/devices/{device_id}/commands", status_code=status.HTTP_201_CREATED)
def send_command(
    device_id: str,
    body: SendCommandRequest,
    db: Session = Depends(get_db),
    username: str = Depends(get_current_user),
) -> dict:
    """Send a command to a device. The device polls for pending commands via MQTT."""
    if body.command_type not in ALLOWED_COMMANDS:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Unknown command '{body.command_type}'. Allowed: {sorted(ALLOWED_COMMANDS)}",
        )
    device = db.query(Device).filter(Device.device_id == device_id).first()
    if not device:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Device not found")

    command = Command(
        device_id=device_id,
        command_type=body.command_type,
        status="sent",
        sent_by=username,
    )
    db.add(command)
    db.commit()
    db.refresh(command)
    return {
        "id": command.id,
        "device_id": command.device_id,
        "command_type": command.command_type,
        "label": COMMAND_LABELS[command.command_type],
        "status": command.status,
        "sent_by": command.sent_by,
        "sent_at": command.sent_at.isoformat() if command.sent_at else None,
    }


@router.get("/api/devices/{device_id}/commands")
def list_device_commands(
    device_id: str,
    limit: int = 20,
    db: Session = Depends(get_db),
    _: str = Depends(get_current_user),
) -> dict:
    """Recent command history for a device."""
    device = db.query(Device).filter(Device.device_id == device_id).first()
    if not device:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Device not found")

    commands = (
        db.query(Command)
        .filter(Command.device_id == device_id)
        .order_by(Command.sent_at.desc())
        .limit(limit)
        .all()
    )
    return {
        "commands": [
            {
                "id": c.id,
                "command_type": c.command_type,
                "label": COMMAND_LABELS.get(c.command_type, c.command_type),
                "status": c.status,
                "result": c.result,
                "error_message": c.error_message,
                "sent_by": c.sent_by,
                "sent_at": c.sent_at.isoformat() if c.sent_at else None,
                "executed_at": c.executed_at.isoformat() if c.executed_at else None,
            }
            for c in commands
        ]
    }


class CommandResultRequest(BaseModel):
    status: str  # executing | success | failed
    result: Optional[str] = None
    error_message: Optional[str] = None


@router.patch("/api/commands/{command_id}")
def update_command_result(
    command_id: int,
    body: CommandResultRequest,
    db: Session = Depends(get_db),
    _: Device = Depends(_get_device_for_command),
) -> dict:
    """Device reports back the result of an executed command."""
    if body.status not in {"executing", "success", "failed"}:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="status must be one of: executing, success, failed",
        )
    command = db.query(Command).filter(Command.id == command_id).first()
    command.status = body.status
    if body.result is not None:
        command.result = body.result
    if body.error_message is not None:
        command.error_message = body.error_message
    if body.status in {"success", "failed"}:
        from datetime import datetime, timezone
        command.executed_at = datetime.now(timezone.utc)

    db.commit()
    return {"id": command.id, "status": command.status}
