from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.database import get_db

router = APIRouter(tags=["health"])


@router.get("/health")
def health(db: Session = Depends(get_db)) -> dict:
    """Health check endpoint."""
    try:
        db.execute(text("SELECT 1"))
        database_status = "connected"
    except Exception:
        database_status = "disconnected"

    return {
        "status": "ok",
        "database": database_status,
        "version": "1.0.0",
    }
