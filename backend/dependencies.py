from fastapi import Depends, HTTPException
from fastapi_jwt_extended import get_jwt, get_jwt_identity, jwt_required

from src.database.db_manager import DatabaseManager

db = DatabaseManager()
ROLE_ORDER = {"viewer": 0, "analyst": 1, "admin": 2}


def require_role(role: str = "viewer"):
    @jwt_required()
    def dependency():
        claims = get_jwt()
        user_role = claims.get("role", "viewer")
        if ROLE_ORDER.get(user_role, -1) < ROLE_ORDER.get(role, 0):
            raise HTTPException(status_code=403, detail="Forbidden")
        user_id = get_jwt_identity()
        user = db.get_user_by_id(user_id)
        if not user or not user.is_active:
            raise HTTPException(status_code=401, detail="Unauthorized")
        return user

    return Depends(dependency)
