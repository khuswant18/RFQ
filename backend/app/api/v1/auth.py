"""Authentication API endpoints."""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional

from app.core.auth import (
    create_access_token, verify_password, get_password_hash,
    get_current_user, DEFAULT_USERS
)

router = APIRouter(tags=["auth"])


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    username: str
    role: str


class UserInfo(BaseModel):
    username: str
    role: str
    full_name: str


@router.post("/auth/login", response_model=TokenResponse)
async def login(request: LoginRequest):
    """Authenticate and get a JWT token."""
    # Dev mode: accept admin/admin123
    if request.username == "admin" and request.password == "admin123":
        token = create_access_token({"sub": "admin", "role": "admin", "name": "SRIP Admin"})
        return TokenResponse(access_token=token, username="admin", role="admin")

    if request.username == "operator" and request.password == "operator123":
        token = create_access_token({"sub": "operator", "role": "operator", "name": "SRIP Operator"})
        return TokenResponse(access_token=token, username="operator", role="operator")

    raise HTTPException(status_code=401, detail="Invalid credentials")


@router.get("/auth/me", response_model=UserInfo)
async def get_me(user: dict = Depends(get_current_user)):
    """Get current user info."""
    return UserInfo(
        username=user.get("username", ""),
        role=user.get("role", ""),
        full_name=user.get("full_name", ""),
    )
