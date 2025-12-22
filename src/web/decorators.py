import functools
import os
from typing import Optional

from flask import jsonify, request
from flask_jwt_extended import get_jwt, get_jwt_identity, verify_jwt_in_request

from src.database.db_manager import DatabaseManager
from src.web.auth import limiter

db = DatabaseManager()

ROLE_ORDER = {"viewer": 0, "analyst": 1, "admin": 2}
ROLE_LIMITS = {"viewer": "100 per minute", "analyst": "1000 per minute", "admin": "2000 per minute"}


def _resolve_user() -> Optional[object]:
    api_key = request.headers.get("X-API-Key")
    if api_key:
        return db.get_user_by_api_key(api_key)
    try:
        verify_jwt_in_request(optional=True)
    except Exception:
        return None
    identity = get_jwt_identity()
    if not identity:
        return None
    return db.get_user_by_id(identity)


def require_role(min_role: str = "viewer"):
    def decorator(fn):
        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            user = _resolve_user()
            if not user or not user.is_active:
                return jsonify({"msg": "Unauthorized"}), 401
            if ROLE_ORDER.get(user.role, -1) < ROLE_ORDER.get(min_role, 0):
                return jsonify({"msg": "Forbidden"}), 403
            return fn(*args, **kwargs)

        limit_value = ROLE_LIMITS.get(min_role, "100 per minute")
        return limiter.limit(limit_value)(wrapper)

    return decorator
