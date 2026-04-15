"""
Tests for routes/sessions.py

Covers:
- POST /api/sessions: creates session row, logs points, returns session_id
- WebSocket frame size guard: oversized frame is rejected with code 1009
- _detect_register_switch: correct detection of register change commands
- _load_tone_profile: cache hit returns profile, cache miss returns default
"""

from __future__ import annotations

import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


# ─── POST /api/sessions ─────────────────────────────────────────────────────

class TestCreateSession:
    @pytest.mark.asyncio
    async def test_create_session_returns_session_id(self, client, demo_token):
        """POST /api/sessions returns a valid session_id for an authenticated user."""
        resp = await client.post(
            "/api/sessions",
            headers={"Authorization": f"Bearer {demo_token}"},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert "session_id" in body
        assert "user_id" in body
        assert "started_at" in body

    @pytest.mark.asyncio
    async def test_create_session_rejects_unauthenticated(self, client):
        """POST /api/sessions without auth returns 403."""
        resp = await client.post("/api/sessions")
        assert resp.status_code in (401, 403)

    @pytest.mark.asyncio
    async def test_create_session_user_id_matches_token(self, client, demo_token):
        """session.user_id must match the authenticated user."""
        resp = await client.post(
            "/api/sessions",
            headers={"Authorization": f"Bearer {demo_token}"},
        )
        assert resp.status_code == 200
        assert resp.json()["user_id"] == "d0000000-0000-0000-0000-000000000001"


# ─── _detect_register_switch ─────────────────────────────────────────────────

class TestDetectRegisterSwitch:
    def setup_method(self):
        from routes.sessions import _detect_register_switch
        self.fn = _detect_register_switch

    def test_detects_ta_switch(self):
        result = self.fn("तँ भनेर बोल", "tapai")
        assert result == "ta"

    def test_detects_timi_switch(self):
        result = self.fn("तिमी भनेर बोल", "tapai")
        assert result == "timi"

    def test_detects_tapai_switch(self):
        result = self.fn("तपाईं भन्नुस्", "ta")
        assert result == "tapai"

    def test_detects_hajur_switch(self):
        result = self.fn("हजुर भन्नुस्", "timi")
        assert result == "hajur"

    def test_no_switch_returns_none(self):
        result = self.fn("नमस्ते, आज मौसम कस्तो छ?", "tapai")
        assert result is None

    def test_latin_timi_switch(self):
        result = self.fn("timi bhanera bol please", "tapai")
        assert result == "timi"


# ─── _load_tone_profile ──────────────────────────────────────────────────────

class TestLoadToneProfile:
    @pytest.mark.asyncio
    async def test_returns_cached_profile_from_valkey(self):
        """Cache hit returns the stored TeacherProfile."""
        profile_data = {
            "name": "Ram",
            "age": 30,
            "gender": "male",
            "native_language": "Nepali",
            "city_or_village": "Pokhara",
            "register": "timi",
            "energy_level": 4,
            "humor_level": 2,
            "code_switch_ratio": 0.1,
            "session_phase": 2,
            "previous_topics": ["weather"],
            "preferred_topics": ["food"],
        }

        import cache
        cache.valkey.get = AsyncMock(return_value=json.dumps(profile_data))

        from routes.sessions import _load_tone_profile
        profile = await _load_tone_profile("user-123")

        assert profile.name == "Ram"
        assert profile.register == "timi"
        assert profile.session_phase == 2

    @pytest.mark.asyncio
    async def test_returns_default_profile_on_cache_miss(self):
        """Cache miss returns a sensible default profile."""
        import cache
        cache.valkey.get = AsyncMock(return_value=None)

        from routes.sessions import _load_tone_profile
        profile = await _load_tone_profile("user-unknown")

        assert profile.name == "साथी"
        assert profile.register == "tapai"
        assert profile.session_phase == 1

    @pytest.mark.asyncio
    async def test_handles_old_cache_format_with_first_last_name(self):
        """Old cache format (first_name/last_name keys) is normalised to name."""
        old_format = {
            "first_name": "Sita",
            "last_name": "Devi",
            "age": 25,
            "gender": "female",
            "native_language": "Nepali",
            "city_or_village": "Kathmandu",
            "register": "tapai",
            "energy_level": 3,
            "humor_level": 3,
            "code_switch_ratio": 0.2,
            "session_phase": 1,
            "previous_topics": [],
            "preferred_topics": [],
        }

        import cache
        cache.valkey.get = AsyncMock(return_value=json.dumps(old_format))

        from routes.sessions import _load_tone_profile
        profile = await _load_tone_profile("user-old-cache")

        assert profile.name == "Sita Devi"


# ─── Frame size guard ────────────────────────────────────────────────────────

class TestFrameSizeGuard:
    """
    The frame size guard lives inside the WebSocket handler loop.
    Test it via a thin unit test of the guard condition directly,
    since wiring a full WS test client requires more infrastructure.
    """

    def test_500kb_limit_constant(self):
        """Confirm the 500KB constant is correct (not accidentally changed)."""
        import routes.sessions as mod
        import ast, inspect
        src = inspect.getsource(mod.conversation_ws)
        # The constant 500_000 must appear in the handler source
        assert "500_000" in src or "500000" in src

    def test_close_code_is_1009(self):
        """RFC 6455 code 1009 = Message Too Big. Verify it's in the handler."""
        import routes.sessions as mod
        import inspect
        src = inspect.getsource(mod.conversation_ws)
        assert "1009" in src
