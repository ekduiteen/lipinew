"""
JWT utility functions shared between routes and dependencies.

Kept in a neutral module to avoid circular imports between
routes/auth.py and dependencies/auth.py.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import HTTPException
from jose import JWTError, jwt

from config import settings


def create_ws_token(user_id: str) -> str:
    """Create a short-lived (5-min) WebSocket-only JWT."""
    expire = datetime.now(timezone.utc) + timedelta(minutes=5)
    payload = {"sub": user_id, "exp": expire, "ws_only": True}
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def create_access_token(user_id: str) -> str:
    """Create a long-lived JWT for a user."""
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.jwt_expire_minutes)
    payload = {"sub": user_id, "exp": expire}
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def create_admin_token(admin_id: str, scope: str = "moderator") -> str:
    """Create a high-privilege JWT for the Control plane."""
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.jwt_expire_minutes)
    payload = {"sub": admin_id, "exp": expire, "ctrl": True, "scope": scope}
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> str:
    """Decode a JWT and return user_id, or raise HTTPException 401."""
    try:
        payload = jwt.decode(
            token, settings.jwt_secret, algorithms=[settings.jwt_algorithm]
        )
        user_id: str | None = payload.get("sub")
        if not user_id:
            raise ValueError("missing sub")
        return user_id
    except JWTError as exc:
        raise HTTPException(status_code=401, detail="Invalid token") from exc
