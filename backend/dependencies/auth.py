"""
JWT FastAPI dependencies.

Usage in routes:
    @router.get("/me")
    async def me(user_id: str = Depends(get_current_user)):
        ...

WS routes use get_ws_user() which reads the token from query params
since browsers cannot send Authorization headers on WebSocket upgrades.
"""

from __future__ import annotations

from fastapi import Depends, HTTPException, Query, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from jwt_utils import decode_access_token

_bearer = HTTPBearer(auto_error=True)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer),
) -> str:
    """Decode Bearer JWT → user_id. Raises 401 on invalid/expired token."""
    return decode_access_token(credentials.credentials)


async def get_current_user_flexible(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(
        HTTPBearer(auto_error=False)
    ),
    token: str = Query(default=""),
) -> str:
    """
    Decode JWT from either:
    - Authorization: Bearer <token>  (standard REST)
    - ?token=<jwt>                    (legacy/stale frontend session proxy)

    Prefer the Authorization header when present.
    """
    if credentials is not None:
        return decode_access_token(credentials.credentials)

    query_token = token or request.query_params.get("token", "")
    if query_token:
        return decode_access_token(query_token)

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Not authenticated",
    )


async def get_current_user_optional(
    credentials: HTTPAuthorizationCredentials | None = Depends(
        HTTPBearer(auto_error=False)
    ),
) -> str | None:
    """Same as get_current_user but returns None instead of raising."""
    if credentials is None:
        return None
    try:
        return decode_access_token(credentials.credentials)
    except HTTPException:
        return None


def get_ws_user(token: str = Query(default="")) -> str:
    """
    Extract user_id from WS query param ?token=<jwt>.
    Raises 401 if missing or invalid.
    Used in WebSocket endpoints where Authorization header is unavailable.
    """
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing token query parameter",
        )
    return decode_access_token(token)
