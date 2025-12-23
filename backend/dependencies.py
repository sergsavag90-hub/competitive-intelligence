import os
from typing import Optional

from fastapi import Depends, HTTPException, Header
from jose import JWTError, jwt

from src.database.db_manager import DatabaseManager

SECRET_KEY = os.getenv("JWT_SECRET", "dev-secret")
ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")

db = DatabaseManager()
ROLE_ORDER = {"viewer": 0, "analyst": 1, "admin": 2}


def require_role(role: str = "viewer"):
    async def dependency(authorization: Optional[str] = Header(default=None)):
        if not authorization or not authorization.lower().startswith("bearer "):
            raise HTTPException(status_code=401, detail="Missing bearer token")
        token = authorization.split(" ", 1)[1]
        try:
            claims = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        except JWTError:
            raise HTTPException(status_code=401, detail="Invalid token")
        user_role = claims.get("role", "viewer")
        if ROLE_ORDER.get(user_role, -1) < ROLE_ORDER.get(role, 0):
            raise HTTPException(status_code=403, detail="Forbidden")
        user_id = claims.get("sub")
        user = db.get_user_by_id(user_id) if user_id else None
        if user is None:
            return {"id": user_id or "anonymous", "role": user_role}
        return user

    return dependency
