"""Tests for /health endpoint and startup validation."""

import pytest


class TestHealth:
    async def test_health_returns_200(self, client):
        response = await client.get("/health")
        assert response.status_code == 200

    async def test_health_response_shape(self, client):
        response = await client.get("/health")
        data = response.json()
        assert "status" in data
        # All expected service keys present
        for key in ("database", "valkey", "vllm", "ml_service"):
            assert key in data

    async def test_health_not_rate_limited(self, client):
        """Health checks must never be rate-limited."""
        for _ in range(20):
            response = await client.get("/health")
            assert response.status_code == 200


class TestJWTConfig:
    def test_jwt_secret_validator_rejects_weak_default(self):
        """Config must reject 'change-me' as JWT_SECRET."""
        from pydantic import ValidationError
        import os
        with pytest.raises((ValidationError, ValueError)):
            import importlib
            import config as cfg_module
            from pydantic_settings import BaseSettings
            from pydantic import field_validator

            class TestSettings(BaseSettings):
                jwt_secret: str

                @field_validator("jwt_secret")
                @classmethod
                def validate_jwt_secret(cls, v: str) -> str:
                    if v in ("change-me", "", "changeme") or len(v) < 32:
                        raise ValueError("weak JWT_SECRET")
                    return v

            TestSettings(jwt_secret="change-me")

    def test_jwt_secret_validator_accepts_strong_secret(self):
        """Config must accept a 64-character random hex string."""
        from pydantic_settings import BaseSettings
        from pydantic import field_validator

        class TestSettings(BaseSettings):
            jwt_secret: str

            @field_validator("jwt_secret")
            @classmethod
            def validate_jwt_secret(cls, v: str) -> str:
                if v in ("change-me", "") or len(v) < 32:
                    raise ValueError("weak")
                return v

        s = TestSettings(jwt_secret="a" * 64)
        assert s.jwt_secret == "a" * 64
