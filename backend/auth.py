import os
from datetime import datetime, timedelta
from typing import Optional

import bcrypt
from fastapi import APIRouter, HTTPException, Response
from jose import JWTError, jwt
from pydantic import BaseModel, EmailStr

from src.database.db_manager import DatabaseManager

router = APIRouter(prefix="/auth", tags=["auth"])
db = DatabaseManager()

SECRET_KEY = os.getenv("JWT_SECRET", "dev-secret")
ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
ACCESS_EXPIRES = timedelta(minutes=int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30")))
REFRESH_EXPIRES = timedelta(days=int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7")))


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    role: str


class RefreshRequest(BaseModel):
    refresh_token: str


def _create_token(subject: str, role: str, token_version: int, expires_delta: timedelta) -> str:
    now = datetime.utcnow()
    payload = {
        "sub": subject,
        "role": role,
        "v": token_version,
        "iat": now,
        "exp": now + expires_delta,
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token: str) -> Optional[dict]:
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError as exc:  # pragma: no cover - handled at call site
        raise HTTPException(status_code=401, detail=str(exc))


def init_jwt(app):
    """Placeholder to keep fastapi_app wiring simple."""
    app.state.jwt_initialized = True


@router.post("/login", response_model=TokenResponse)
def login(data: LoginRequest, response: Response):
    user = db.authenticate_user(data.email, data.password)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials or locked")

    access = _create_token(user.id, user.role, getattr(user, "token_version", 0), ACCESS_EXPIRES)
    refresh = _create_token(user.id, user.role, getattr(user, "token_version", 0), REFRESH_EXPIRES)
    return TokenResponse(access_token=access, refresh_token=refresh, role=user.role)


@router.post("/refresh", response_model=TokenResponse)
def refresh(payload: RefreshRequest):
    decoded = decode_token(payload.refresh_token)
    sub = decoded.get("sub")
    role = decoded.get("role", "viewer")
    version = decoded.get("v", 0)
    new_access = _create_token(sub, role, version, ACCESS_EXPIRES)
    new_refresh = _create_token(sub, role, version, REFRESH_EXPIRES)
    return TokenResponse(access_token=new_access, refresh_token=new_refresh, role=role)


@router.get("/me")
def me(token: str):
    decoded = decode_token(token)
    return {"sub": decoded.get("sub"), "role": decoded.get("role")}
