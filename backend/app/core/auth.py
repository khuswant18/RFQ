"""JWT Authentication and Role-Based Access Control."""
import os
from datetime import datetime, timedelta
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

# JWT dependencies — graceful fallback
try:
    from jose import JWTError, jwt
    JWT_AVAILABLE = True
except ImportError:
    JWT_AVAILABLE = False

try:
    from passlib.context import CryptContext
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
    PASSLIB_AVAILABLE = True
except ImportError:
    PASSLIB_AVAILABLE = False
    pwd_context = None

# Configuration
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "srip-dev-secret-key-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("JWT_EXPIRE_MINUTES", "480"))  # 8 hours

security = HTTPBearer(auto_error=False)

# Default users (in production, use a database)
DEFAULT_USERS = {
    "admin": {
        "username": "admin",
        "hashed_password": "$2b$12$LJ3f3W0KV9Z5Z5Z5Z5Z5ZuWV1Z5Z5Z5Z5Z5Z5Z5Z5Z5Z5Z5Z5Z",  # placeholder
        "role": "admin",
        "full_name": "SRIP Admin",
    },
    "operator": {
        "username": "operator",
        "hashed_password": "$2b$12$placeholder",
        "role": "operator",
        "full_name": "SRIP Operator",
    },
}


def verify_password(plain_password: str, hashed_password: str) -> bool:
    if not PASSLIB_AVAILABLE:
        return plain_password == "admin123"  # Dev fallback
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    if not PASSLIB_AVAILABLE:
        return password
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    if not JWT_AVAILABLE:
        return "dev-token-jwt-not-available"
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token: str) -> Optional[dict]:
    if not JWT_AVAILABLE:
        return {"sub": "admin", "role": "admin"} if token else None
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return None


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> dict:
    """FastAPI dependency to get the current authenticated user.
    If AUTH_REQUIRED=false (default for dev), allows unauthenticated access."""
    auth_required = os.getenv("AUTH_REQUIRED", "false").lower() == "true"

    if not auth_required:
        return {"username": "dev", "role": "admin", "full_name": "Dev User"}

    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    payload = decode_token(credentials.credentials)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )

    return {
        "username": payload.get("sub"),
        "role": payload.get("role", "operator"),
        "full_name": payload.get("name", ""),
    }


def require_role(required_role: str):
    """Dependency factory for role-based access."""
    async def role_checker(user: dict = Depends(get_current_user)):
        if user.get("role") != required_role and user.get("role") != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{required_role}' required",
            )
        return user
    return role_checker
