"""Tests for /api/auth/* endpoints."""

import pytest
from unittest.mock import AsyncMock, patch


class TestDemoLogin:
    async def test_demo_login_returns_200_in_dev(self, client):
        response = await client.post("/api/auth/demo")
        assert response.status_code == 200

    async def test_demo_login_returns_token(self, client):
        response = await client.post("/api/auth/demo")
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert data["onboarding_complete"] is True

    async def test_demo_login_creates_user(self, client):
        response = await client.post("/api/auth/demo")
        assert response.status_code == 200
        # Second call should also succeed (user already exists)
        response2 = await client.post("/api/auth/demo")
        assert response2.status_code == 200

    async def test_demo_login_blocked_in_production(self, client, monkeypatch):
        monkeypatch.setenv("ENVIRONMENT", "production")
        # Re-import settings to pick up the env change
        import config
        from unittest.mock import patch
        with patch.object(config.settings, "environment", "production"):
            response = await client.post("/api/auth/demo")
        assert response.status_code == 403


class TestJWTRefresh:
    async def test_refresh_with_valid_token(self, client, demo_token):
        # First get a valid token via demo login
        login_resp = await client.post("/api/auth/demo")
        token = login_resp.json()["access_token"]

        # Refresh it
        response = await client.post(f"/api/auth/refresh?old_token={token}")
        assert response.status_code == 200
        assert "access_token" in response.json()

    async def test_refresh_with_invalid_token(self, client):
        response = await client.post("/api/auth/refresh?old_token=not-a-real-token")
        assert response.status_code == 401


class TestWSToken:
    async def test_ws_token_requires_auth(self, client):
        response = await client.post("/api/auth/ws-token")
        assert response.status_code == 403  # No bearer token

    async def test_ws_token_with_valid_auth(self, client):
        # Get a token first
        login_resp = await client.post("/api/auth/demo")
        token = login_resp.json()["access_token"]

        response = await client.post(
            "/api/auth/ws-token",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        assert "ws_token" in response.json()

    async def test_ws_token_is_short_lived(self, client):
        """WS token should decode correctly and have ws_only claim."""
        login_resp = await client.post("/api/auth/demo")
        token = login_resp.json()["access_token"]

        ws_resp = await client.post(
            "/api/auth/ws-token",
            headers={"Authorization": f"Bearer {token}"},
        )
        ws_token = ws_resp.json()["ws_token"]

        # Decode and verify ws_only claim
        from jose import jwt
        from config import settings
        payload = jwt.decode(ws_token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
        assert payload.get("ws_only") is True
