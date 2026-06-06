from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models.error import ErrorType, RepairAction, RepairOutcome

router = APIRouter(prefix="/api/errors", tags=["errors"])


# ─── Helpers ──────────────────────────────────────────────────────────────────


def _serialize_action(a: RepairAction) -> dict:
    return {
        "id": a.id,
        "step": a.step_order,
        "action": a.action,
        "description": a.description,
        "estimated_time": a.estimated_time_minutes,
        "success_rate": a.success_rate,
        "occurrences": a.occurrences,
        "successful_occurrences": a.successful_occurrences,
    }


def _serialize_error_type(et: ErrorType, actions: list[RepairAction]) -> dict:
    return {
        "id": et.id,
        "error_code": et.error_code,
        "display_name": et.display_name,
        "description": et.description,
        "severity": et.severity,
        "repair_actions": [_serialize_action(a) for a in actions],
    }


def _get_error_type_or_404(error_code: str, db: Session) -> ErrorType:
    et = db.query(ErrorType).filter(ErrorType.error_code == error_code).first()
    if not et:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Error type '{error_code}' not found")
    return et


# ─── Routes ───────────────────────────────────────────────────────────────────


@router.get("")
def list_error_types(
    db: Session = Depends(get_db),
    _: str = Depends(get_current_user),
) -> dict:
    """List all known error types with their repair actions."""
    error_types = db.query(ErrorType).order_by(ErrorType.display_name).all()
    result = []
    for et in error_types:
        actions = (
            db.query(RepairAction)
            .filter(RepairAction.error_id == et.id)
            .order_by(RepairAction.step_order)
            .all()
        )
        result.append(_serialize_error_type(et, actions))
    return {"error_types": result}


@router.get("/{error_code}")
def get_error_type(
    error_code: str,
    db: Session = Depends(get_db),
    _: str = Depends(get_current_user),
) -> dict:
    """Get a single error type with its repair actions."""
    et = _get_error_type_or_404(error_code, db)
    actions = (
        db.query(RepairAction)
        .filter(RepairAction.error_id == et.id)
        .order_by(RepairAction.step_order)
        .all()
    )
    return _serialize_error_type(et, actions)


class OutcomeRequest(BaseModel):
    device_id: str
    repair_action_id: Optional[int] = None
    worked: bool
    notes: Optional[str] = None
    time_spent_minutes: Optional[int] = None


@router.post("/{error_code}/outcomes", status_code=status.HTTP_201_CREATED)
def record_outcome(
    error_code: str,
    body: OutcomeRequest,
    db: Session = Depends(get_db),
    username: str = Depends(get_current_user),
) -> dict:
    """Record a repair outcome and update the repair action's success rate."""
    et = _get_error_type_or_404(error_code, db)

    outcome = RepairOutcome(
        device_id=body.device_id,
        error_id=et.id,
        repair_action_id=body.repair_action_id,
        worked=body.worked,
        notes=body.notes,
        time_spent_minutes=body.time_spent_minutes,
        attempted_by=username,
    )
    db.add(outcome)

    # Update success rate on the specific repair action
    if body.repair_action_id:
        action = db.query(RepairAction).filter(
            RepairAction.id == body.repair_action_id,
            RepairAction.error_id == et.id,
        ).first()
        if not action:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Repair action {body.repair_action_id} not found for error '{error_code}'",
            )
        if action:
            action.occurrences += 1
            if body.worked:
                action.successful_occurrences += 1
            action.success_rate = action.successful_occurrences / action.occurrences

    db.commit()
    db.refresh(outcome)
    return {"id": outcome.id, "worked": body.worked, "recorded_by": username}


class AddActionRequest(BaseModel):
    action: str
    description: Optional[str] = None
    estimated_time_minutes: Optional[int] = None


@router.post("/{error_code}/actions", status_code=status.HTTP_201_CREATED)
def add_repair_action(
    error_code: str,
    body: AddActionRequest,
    db: Session = Depends(get_db),
    username: str = Depends(get_current_user),
) -> dict:
    """Add a new repair action to a known error type."""
    et = _get_error_type_or_404(error_code, db)

    # Place at the end of the existing steps
    last_step = (
        db.query(RepairAction)
        .filter(RepairAction.error_id == et.id)
        .order_by(RepairAction.step_order.desc())
        .first()
    )
    next_step = (last_step.step_order + 1) if last_step else 1

    action = RepairAction(
        error_id=et.id,
        step_order=next_step,
        action=body.action,
        description=body.description,
        estimated_time_minutes=body.estimated_time_minutes,
        created_by=username,
    )
    db.add(action)
    db.commit()
    db.refresh(action)
    return _serialize_action(action)
