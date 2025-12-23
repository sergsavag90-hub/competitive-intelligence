import os
from datetime import datetime, timedelta
from typing import Optional

import bcrypt
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from jose import JWTError, jwt
from pydantic import BaseModel, EmailStr

from src.database.db_manager import DatabaseManager

router = APIRouter(prefix="/auth", tags=["auth"])
db = DatabaseManager()

SECRET_KEY = os.getenv("JWT_SECRET", "dev-secret")
ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
ACCESS_EXPIRES = timedelta(minutes=int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "15")))
REFRESH_EXPIRES = timedelta(days=int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7")))
ACCESS_COOKIE = os.getenv("ACCESS_TOKEN_COOKIE_NAME", "ci_access_token")
REFRESH_COOKIE = os.getenv("REFRESH_TOKEN_COOKIE_NAME", "ci_refresh_token")
COOKIE_SECURE = os.getenv("COOKIE_SECURE", "false").lower() == "true"
COOKIE_SAMESITE = os.getenv("COOKIE_SAMESITE", "lax")
AUTH_RATE_LIMIT = int(os.getenv("AUTH_RATE_LIMIT_PER_MIN", "20"))

# Very lightweight in-memory rate limiter keyed by client IP.
_RATE_BUCKETS: dict[str, list[float]] = {}


def _check_rate_limit(request: Request):
    if AUTH_RATE_LIMIT <= 0:
        return
    now = datetime.utcnow().timestamp()
    bucket = _RATE_BUCKETS.setdefault(request.client.host, [])
    bucket[:] = [ts for ts in bucket if now - ts <= 60]
    if len(bucket) >= AUTH_RATE_LIMIT:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many auth attempts. Please slow down.",
        )
    bucket.append(now)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    role: str = "viewer"


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    role: str


class RefreshRequest(BaseModel):
    refresh_token: Optional[str] = None


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


def _set_token_cookies(response: Response, access: str, refresh: str):
    response.set_cookie(
        key=ACCESS_COOKIE,
        value=access,
        httponly=True,
        secure=COOKIE_SECURE,
        samesite=COOKIE_SAMESITE,
        max_age=int(ACCESS_EXPIRES.total_seconds()),
        path="/",
    )
    response.set_cookie(
        key=REFRESH_COOKIE,
        value=refresh,
        httponly=True,
        secure=COOKIE_SECURE,
        samesite=COOKIE_SAMESITE,
        max_age=int(REFRESH_EXPIRES.total_seconds()),
        path="/",
    )


def _issue_tokens(user, response: Response) -> TokenResponse:
    access = _create_token(user.id, user.role, getattr(user, "token_version", 0), ACCESS_EXPIRES)
    refresh = _create_token(user.id, user.role, getattr(user, "token_version", 0), REFRESH_EXPIRES)
    _set_token_cookies(response, access, refresh)
    return TokenResponse(access_token=access, refresh_token=refresh, role=user.role)


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def register(data: RegisterRequest, response: Response, request: Request = None, _=Depends(_check_rate_limit)):
    if db.get_user_by_email(data.email):
        raise HTTPException(status_code=400, detail="User already exists")
    user = db.create_user(data.email, data.password, data.role)
    return _issue_tokens(user, response)


@router.post("/login", response_model=TokenResponse)
def login(data: LoginRequest, response: Response, request: Request, _=Depends(_check_rate_limit)):
    user = db.authenticate_user(data.email, data.password)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials or locked")
    return _issue_tokens(user, response)


@router.post("/refresh", response_model=TokenResponse)
def refresh(payload: RefreshRequest, response: Response, request: Request, _=Depends(_check_rate_limit)):
    supplied_token = payload.refresh_token or request.cookies.get(REFRESH_COOKIE)
    if not supplied_token:
        raise HTTPException(status_code=401, detail="Missing refresh token")
    decoded = decode_token(supplied_token)
    sub = decoded.get("sub")
    role = decoded.get("role", "viewer")
    version = decoded.get("v", 0)
    new_access = _create_token(sub, role, version, ACCESS_EXPIRES)
    new_refresh = _create_token(sub, role, version, REFRESH_EXPIRES)
    _set_token_cookies(response, new_access, new_refresh)
    return TokenResponse(access_token=new_access, refresh_token=new_refresh, role=role)


@router.get("/me")
def me(request: Request, token: Optional[str] = None):
    token = token or request.cookies.get(ACCESS_COOKIE)
    if not token:
        raise HTTPException(status_code=401, detail="Missing access token")
    decoded = decode_token(token)
    return {"sub": decoded.get("sub"), "role": decoded.get("role")}
