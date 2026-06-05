from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from app.utils.security import create_access_token, verify_password

router = APIRouter(prefix="/api/auth", tags=["auth"])

# Phase 1: hardcoded users. Replace with DB-backed auth in Phase 1.5.
USERS = {
    "support": "$2b$12$s6u40ZhG5s/lk0n93xdT1.ehj6jrDojEu9A1bU7I8pBkaNmAx/CPy",  # support123
    "admin":   "$2b$12$s6u40ZhG5s/lk0n93xdT1.ehj6jrDojEu9A1bU7I8pBkaNmAx/CPy",  # support123
}


class LoginRequest(BaseModel):
    """Dashboard login credentials."""
    username: str
    password: str


class LoginResponse(BaseModel):
    """JWT response on successful login."""
    access_token: str
    token_type: str = "bearer"


@router.post("/login", response_model=LoginResponse)
def login(body: LoginRequest) -> LoginResponse:
    """Authenticate a dashboard user and return a JWT."""
    hashed = USERS.get(body.username)
    if not hashed or not verify_password(body.password, hashed):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
        )
    return LoginResponse(access_token=create_access_token(body.username))
