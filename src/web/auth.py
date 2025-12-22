import os
import smtplib
import secrets
from email.message import EmailMessage
from typing import Optional

from flask import Blueprint, current_app, jsonify, request
from flask_jwt_extended import (
    JWTManager,
    create_access_token,
    create_refresh_token,
    get_jwt,
    get_jwt_identity,
    jwt_required,
)
from flask_wtf import CSRFProtect
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

from src.database.db_manager import DatabaseManager


jwt = JWTManager()
csrf = CSRFProtect()
limiter = Limiter(key_func=get_remote_address, storage_uri=os.getenv("REDIS_URL", "memory://"))

auth_bp = Blueprint("auth", __name__, url_prefix="/auth")
db = DatabaseManager()


def init_security(app):
    app.config.setdefault("JWT_SECRET_KEY", os.getenv("JWT_SECRET_KEY", "change-me"))
    app.config.setdefault("JWT_ACCESS_TOKEN_EXPIRES", 3600)
    app.config.setdefault("JWT_REFRESH_TOKEN_EXPIRES", 86400)
    jwt.init_app(app)
    csrf.init_app(app)
    limiter.init_app(app)
    app.register_blueprint(auth_bp)


def _send_reset_email(email: str, token: str) -> None:
    smtp_server = os.getenv("SMTP_SERVER")
    smtp_port = int(os.getenv("SMTP_PORT", "587"))
    smtp_username = os.getenv("SMTP_USERNAME")
    smtp_password = os.getenv("SMTP_PASSWORD")
    smtp_from = os.getenv("SMTP_FROM", smtp_username or "noreply@example.com")
    if not smtp_server or not smtp_username or not smtp_password:
        current_app.logger.warning("SMTP not configured; skipping password reset email.")
        return
    msg = EmailMessage()
    msg["Subject"] = "Password reset"
    msg["From"] = smtp_from
    msg["To"] = email
    reset_link = f"{request.url_root.rstrip('/')}/auth/reset-password?token={token}"
    msg.set_content(f"Use the following link to reset your password: {reset_link}")
    with smtplib.SMTP(smtp_server, smtp_port) as server:
        server.starttls()
        server.login(smtp_username, smtp_password)
        server.send_message(msg)


@auth_bp.route("/register", methods=["POST"])
@jwt_required()
def register_user():
    claims = get_jwt()
    if claims.get("role") != "admin":
        return jsonify({"msg": "Forbidden"}), 403
    data = request.get_json() or {}
    email = data.get("email")
    password = data.get("password")
    role = data.get("role", "viewer")
    if not email or not password:
        return jsonify({"msg": "Email and password required"}), 400
    user = db.create_user(email=email, password=password, role=role)
    db.log_audit(claims.get("sub"), "access", "register_user", request.remote_addr, request.user_agent.string)
    return jsonify({"id": user.id, "email": user.email, "role": user.role}), 201


@auth_bp.route("/login", methods=["POST"])
@limiter.limit("10/minute")
def login():
    data = request.get_json() or {}
    email = data.get("email")
    password = data.get("password")
    if not email or not password:
        return jsonify({"msg": "Email and password required"}), 400
    user = db.authenticate_user(email, password)
    if not user:
        return jsonify({"msg": "Invalid credentials or locked"}), 401
    additional_claims = {"role": user.role}
    access = create_access_token(identity=user.id, additional_claims=additional_claims)
    refresh = create_refresh_token(identity=user.id, additional_claims=additional_claims)
    db.log_audit(user.id, "login", "login", request.remote_addr, request.user_agent.string)
    return jsonify({"access_token": access, "refresh_token": refresh})


@auth_bp.route("/refresh", methods=["POST"])
@jwt_required(refresh=True)
def refresh():
    identity = get_jwt_identity()
    claims = get_jwt()
    new_access = create_access_token(identity=identity, additional_claims={"role": claims.get("role")})
    db.log_audit(identity, "access", "refresh", request.remote_addr, request.user_agent.string)
    return jsonify({"access_token": new_access})


@auth_bp.route("/api-key", methods=["POST"])
@jwt_required()
def issue_api_key():
    user_id = get_jwt_identity()
    api_key = db.generate_api_key(user_id)
    db.log_audit(user_id, "access", "issue_api_key", request.remote_addr, request.user_agent.string)
    return jsonify({"api_key": api_key})


@auth_bp.route("/api-key", methods=["DELETE"])
@jwt_required()
def revoke_api_key():
    user_id = get_jwt_identity()
    db.revoke_api_key(user_id)
    db.log_audit(user_id, "access", "revoke_api_key", request.remote_addr, request.user_agent.string)
    return jsonify({"msg": "revoked"})


@auth_bp.route("/request-reset", methods=["POST"])
@limiter.limit("5/hour")
def request_reset():
    data = request.get_json() or {}
    email = data.get("email")
    if not email:
        return jsonify({"msg": "Email required"}), 400
    user = db.get_user_by_email(email)
    if not user:
        return jsonify({"msg": "If the account exists, an email will be sent"}), 200
    token = secrets.token_urlsafe(24)
    # store token in Redis with TTL 15m
    redis_client = getattr(limiter, "storage", None)
    if redis_client and hasattr(redis_client, "set"):
        try:
            redis_client.set(f"reset:{token}", user.id, ex=900)
        except Exception:
            current_app.logger.warning("Could not store reset token; skipping.")
    _send_reset_email(email, token)
    return jsonify({"msg": "If the account exists, an email will be sent"}), 200


@auth_bp.route("/reset-password", methods=["POST"])
def reset_password():
    data = request.get_json() or {}
    token = data.get("token")
    new_password = data.get("password")
    if not token or not new_password:
        return jsonify({"msg": "Token and new password required"}), 400
    redis_client = getattr(limiter, "storage", None)
    user_id: Optional[str] = None
    if redis_client and hasattr(redis_client, "get"):
        try:
            user_id = redis_client.get(f"reset:{token}")
        except Exception:
            pass
    if not user_id:
        return jsonify({"msg": "Invalid or expired token"}), 400
    user = db.get_user_by_id(user_id)
    if not user:
        return jsonify({"msg": "Invalid token"}), 400
    db.update_password(user.id, new_password)
    db.backend._reset_failed_attempts(user.id)
    db.log_audit(user.id, "access", "reset_password", request.remote_addr, request.user_agent.string)
    if redis_client and hasattr(redis_client, "delete"):
        try:
            redis_client.delete(f"reset:{token}")
        except Exception:
            pass
    return jsonify({"msg": "Password updated"}), 200
