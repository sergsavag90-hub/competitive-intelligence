import os
from datetime import timedelta
from typing import Optional

import bcrypt
from fastapi import APIRouter, Depends, HTTPException, Response, Request
from fastapi_jwt_extended import (
    JWTManager,
    create_access_token,
    create_refresh_token,
    get_jwt,
    get_jwt_identity,
    jwt_required,
    set_access_cookies,
    set_refresh_cookies,
    unset_jwt_cookies,
)
from pydantic import BaseModel, EmailStr

from src.database.db_manager import DatabaseManager

router = APIRouter(prefix="/auth", tags=["auth"])
db = DatabaseManager()
jwt = JWTManager()


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    role: str


def init_jwt(app):
    app.state.jwt_initialized = True
    app.config = getattr(app, "config", {})
    app.config["JWT_SECRET_KEY"] = os.getenv("JWT_SECRET_KEY", "change-me")
    app.config["JWT_TOKEN_LOCATION"] = ["cookies"]
    app.config["JWT_COOKIE_SECURE"] = False
    app.config["JWT_COOKIE_CSRF_PROTECT"] = True
    app.config["JWT_ACCESS_TOKEN_EXPIRES"] = timedelta(hours=1)
    app.config["JWT_REFRESH_TOKEN_EXPIRES"] = timedelta(days=7)
    jwt.init_app(app)


@router.post("/login", response_model=TokenResponse)
def login(data: LoginRequest, response: Response):
    user = db.authenticate_user(data.email, data.password)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials or locked")

    claims = {"role": user.role}
    access = create_access_token(identity=user.id, additional_claims=claims)
    refresh = create_refresh_token(identity=user.id, additional_claims=claims)
    set_access_cookies(response, access)
    set_refresh_cookies(response, refresh)
    return TokenResponse(access_token=access, refresh_token=refresh, role=user.role)


@router.post("/refresh", response_model=TokenResponse)
@jwt_required(refresh=True)
def refresh(response: Response):
    identity = get_jwt_identity()
    claims = get_jwt()
    access = create_access_token(identity=identity, additional_claims={"role": claims.get("role")})
    set_access_cookies(response, access)
    return TokenResponse(access_token=access, refresh_token="", role=claims.get("role"))


@router.post("/logout")
def logout(response: Response):
    unset_jwt_cookies(response)
    return {"msg": "logged out"}


@router.get("/me")
@jwt_required()
def me():
    return {"sub": get_jwt_identity(), "role": get_jwt().get("role")}
