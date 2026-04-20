"""
Auth routes — JWT issuance + Google OAuth exchange.
Phone auth (OTP) is Phase 2; skeleton is here for wiring.
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone

import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from db.connection import get_db
from dependencies.auth import get_current_user
from jwt_utils import create_access_token, create_ws_token, decode_access_token
from models.user import User
from rate_limit import limiter

router = APIRouter(prefix="/api/auth", tags=["auth"])
logger = logging.getLogger("lipi.backend.auth")

_GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
_GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v3/userinfo"


# ─── Schemas ────────────────────────────────────────────────────────────────

class GoogleCallbackRequest(BaseModel):
    code: str
    redirect_uri: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user_id: str
    onboarding_complete: bool


# ─── User upsert ────────────────────────────────────────────────────────────

async def _upsert_google_user(
    db: AsyncSession,
    google_sub: str,
    email: str | None,
    first_name: str,
    last_name: str | None,
) -> User:
    """
    Find or create a user by Google provider ID.
    Returns the User ORM object (not yet committed — caller must commit).
    """
    result = await db.execute(
        select(User).where(
            User.auth_provider == "google",
            User.auth_provider_id == google_sub,
        )
    )
    user = result.scalar_one_or_none()

    if user is None:
        user = User(
            id=str(uuid.uuid4()),
            auth_provider="google",
            auth_provider_id=google_sub,
            email=email,
            first_name=first_name,
            last_name=last_name,
        )
        db.add(user)
        logger.info("New user created via Google auth: %s", user.id)
    else:
        # Update mutable fields that may change on re-login
        if email:
            user.email = email
        user.first_name = first_name
        if last_name:
            user.last_name = last_name
        user.last_seen_at = datetime.now(timezone.utc)

    await db.flush()
    return user


# ─── Endpoints ──────────────────────────────────────────────────────────────

@limiter.limit("5/minute")  # 5 auth attempts per minute per IP
@router.post("/google", response_model=TokenResponse)
async def google_callback(
    body: GoogleCallbackRequest,
    db: AsyncSession = Depends(get_db),
    request = None,  # Injected by rate limiter
) -> TokenResponse:
    """Exchange Google OAuth code for a LIPI JWT."""
    async with httpx.AsyncClient(timeout=10.0) as client:
        # Exchange code for Google tokens
        token_resp = await client.post(
            _GOOGLE_TOKEN_URL,
            data={
                "code": body.code,
                "client_id": settings.google_client_id,
                "client_secret": settings.google_client_secret,
                "redirect_uri": body.redirect_uri,
                "grant_type": "authorization_code",
            },
        )
        if token_resp.status_code != 200:
            google_error = token_resp.text
            logger.error(
                "Google token exchange failed: status=%d, body=%s, redirect_uri=%s",
                token_resp.status_code,
                google_error,
                body.redirect_uri,
            )
            raise HTTPException(status_code=400, detail=f"Google token exchange failed: {google_error}")

        google_tokens = token_resp.json()

        # Fetch userinfo
        userinfo_resp = await client.get(
            _GOOGLE_USERINFO_URL,
            headers={"Authorization": f"Bearer {google_tokens['access_token']}"},
        )
        if userinfo_resp.status_code != 200:
            raise HTTPException(status_code=400, detail="Failed to fetch Google user info")

        userinfo = userinfo_resp.json()

    google_sub: str = userinfo["sub"]
    email: str | None = userinfo.get("email")
    first_name: str = userinfo.get("given_name") or userinfo.get("name", "Teacher")
    last_name: str | None = userinfo.get("family_name")

    user = await _upsert_google_user(db, google_sub, email, first_name, last_name)
    await db.commit()

    token = create_access_token(user.id)
    return TokenResponse(
        access_token=token,
        expires_in=settings.jwt_expire_minutes * 60,
        user_id=user.id,
        onboarding_complete=user.onboarding_complete,
    )


@limiter.limit("3/minute")  # Stricter limit for demo login
@router.post("/demo", response_model=TokenResponse)
async def demo_login(db: AsyncSession = Depends(get_db), request = None) -> TokenResponse:
    """
    Dev-only demo login — creates a seeded teacher and returns a JWT.
    Returns 403 in any non-development environment.
    """
    if settings.environment != "development":
        raise HTTPException(status_code=403, detail="Demo login is only available in development")

    _DEMO_ID = "d0000000-0000-0000-0000-000000000001"

    user = await db.get(User, _DEMO_ID)
    if user is None:
        user = User(
            id=_DEMO_ID,
            auth_provider="google",
            auth_provider_id="demo",
            first_name="Demo",
            last_name="Teacher",
            email="demo@lipi.local",
            primary_language="Nepali",
            hometown="Kathmandu",
            age=28,
            gender="other",
            education_level="bachelors",
            consent_audio_training=True,
            consent_leaderboard_name=True,
        )
        db.add(user)
        await db.flush()

    # Mark onboarding complete if not already
    if not user.onboarding_complete:
        user.onboarding_complete = True
        await db.flush()

    # Seed points summary so the home screen shows something
    from models.points import TeacherPointsSummary
    from datetime import date
    summary = await db.get(TeacherPointsSummary, _DEMO_ID)
    if summary is None:
        summary = TeacherPointsSummary(
            teacher_id=_DEMO_ID,
            total_points=420,
            points_this_week=85,
            points_this_month=210,
            total_words_taught=47,
            total_sessions=12,
            current_streak_days=5,
            longest_streak_days=14,
            week_start=date.today(),
            month_start=date.today().replace(day=1),
        )
        db.add(summary)

    # Cache tone profile in Valkey
    import json
    from cache import valkey
    tone_key = f"user:{_DEMO_ID}:tone_profile"
    if not await valkey.exists(tone_key):
        await valkey.setex(tone_key, 86400, json.dumps({
            "name": "Demo Teacher",
            "age": 28,
            "gender": "other",
            "native_language": "Nepali",
            "city_or_village": "Kathmandu",
            "register": "tapai",
            "energy_level": 3,
            "humor_level": 3,
            "code_switch_ratio": 0.2,
            "session_phase": 1,
            "previous_topics": [],
            "preferred_topics": [],
        }))

    await db.commit()

    token = create_access_token(_DEMO_ID)
    return TokenResponse(
        access_token=token,
        expires_in=settings.jwt_expire_minutes * 60,
        user_id=_DEMO_ID,
        onboarding_complete=True,
    )


@limiter.limit("3/minute")  # Stricter limit for demo admin login
@router.post("/demo-admin")
async def demo_admin_login(db: AsyncSession = Depends(get_db), request = None):
    """
    Dev-only demo admin login for frontend-control dashboard.
    Creates or retrieves a seeded admin and returns an admin JWT with ctrl scope.
    Returns 403 in any non-development environment.
    """
    if settings.environment != "development":
        raise HTTPException(status_code=403, detail="Demo admin login is only available in development")

    from models.admin_control import AdminAccount

    _DEMO_ADMIN_ID = "a0000000-0000-0000-0000-000000000001"

    admin = await db.get(AdminAccount, _DEMO_ADMIN_ID)
    if admin is None:
        admin = AdminAccount(
            id=_DEMO_ADMIN_ID,
            email="demo-admin@lipi.local",
            full_name="Demo Admin",
            role="super_admin",
            is_active=True,
        )
        db.add(admin)
        await db.flush()

    await db.commit()

    # Create admin token with ctrl scope
    from jwt_utils import create_admin_token
    token = create_admin_token(_DEMO_ADMIN_ID, scope="super_admin")

    return {
        "access_token": token,
        "token_type": "bearer",
        "expires_in": settings.jwt_expire_minutes * 60,
        "admin_id": _DEMO_ADMIN_ID,
        "role": "super_admin",
        "full_name": "Demo Admin",
    }


@limiter.limit("10/minute")  # Token refresh, can be called more frequently
@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    old_token: str,
    db: AsyncSession = Depends(get_db),
    request = None,
) -> TokenResponse:
    """Issue a new JWT from a still-valid one (sliding expiry)."""
    user_id = decode_access_token(old_token)
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    new_token = create_access_token(user_id)
    return TokenResponse(
        access_token=new_token,
        expires_in=settings.jwt_expire_minutes * 60,
        user_id=user_id,
        onboarding_complete=user.onboarding_complete,
    )


class WSTokenResponse(BaseModel):
    ws_token: str


@limiter.limit("20/minute")  # WebSocket token requests, can be frequent
@router.post("/ws-token", response_model=WSTokenResponse)
async def get_ws_token(user_id: str = Depends(get_current_user), request = None) -> WSTokenResponse:
    """Issue a short-lived token for WebSocket upgrade (5-min expiry).

    The httpOnly cookie transport doesn't support custom headers on WebSocket,
    so this endpoint issues a token valid only for WS connections.
    """
    return WSTokenResponse(ws_token=create_ws_token(user_id))
