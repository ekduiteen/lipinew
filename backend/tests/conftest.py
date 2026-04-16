"""Shared pytest fixtures for LIPI backend tests."""

import asyncio
import os
from typing import AsyncIterator
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

# SQLite doesn't support PostgreSQL-specific types — teach the SQLite compiler about them
from sqlalchemy.dialects.sqlite.base import SQLiteTypeCompiler as _SQLiteTypeCompiler

def _visit_JSONB(self, type_, **kw):  # noqa: N802
    return "JSON"

_SQLiteTypeCompiler.visit_JSONB = _visit_JSONB

# Use aiosqlite for fast in-memory tests (no Postgres needed)
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

# Patch the settings before importing the app
os.environ.setdefault("JWT_SECRET", "test-secret-key-for-testing-only-32chars")
os.environ.setdefault("ENVIRONMENT", "development")
os.environ.setdefault("DATABASE_URL", TEST_DATABASE_URL)
os.environ.setdefault("VALKEY_URL", "valkey://localhost:6379/0")
os.environ.setdefault("VLLM_URL", "http://localhost:8100")
os.environ.setdefault("ML_SERVICE_URL", "http://localhost:5001")
os.environ.setdefault("MINIO_ENDPOINT", "localhost:9000")
os.environ.setdefault("GOOGLE_CLIENT_ID", "test-google-client-id")
os.environ.setdefault("GOOGLE_CLIENT_SECRET", "test-google-client-secret")


@pytest.fixture(scope="session")
def event_loop_policy():
    return asyncio.DefaultEventLoopPolicy()


@pytest.fixture
async def db_engine():
    """Provide an in-memory SQLite async engine per test."""
    from models.base import Base
    import models.user     # noqa: F401 — register models
    import models.session  # noqa: F401
    import models.message  # noqa: F401
    import models.points   # noqa: F401
    import models.badge    # noqa: F401
    import models.curriculum  # noqa: F401
    import models.intelligence  # noqa: F401
    import models.phrases  # noqa: F401

    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest.fixture
async def db_session(db_engine) -> AsyncIterator[AsyncSession]:
    """Provide a clean DB session per test, rolled back after each test."""
    session_factory = async_sessionmaker(db_engine, expire_on_commit=False)
    async with session_factory() as session:
        yield session
        await session.rollback()


@pytest.fixture
def mock_valkey():
    """Mock Valkey client — avoids real Redis connection in tests."""
    mock = AsyncMock()
    mock.ping = AsyncMock(return_value=True)
    mock.get = AsyncMock(return_value=None)
    mock.set = AsyncMock(return_value=True)
    mock.setex = AsyncMock(return_value=True)
    mock.exists = AsyncMock(return_value=False)
    mock.lpush = AsyncMock(return_value=1)
    mock.brpoplpush = AsyncMock(return_value=None)
    mock.lrem = AsyncMock(return_value=1)
    mock.aclose = AsyncMock(return_value=None)
    return mock


@pytest.fixture
def mock_http_client():
    """Mock httpx.AsyncClient for STT/TTS/LLM calls."""
    mock = AsyncMock()
    mock.aclose = AsyncMock(return_value=None)
    return mock


@pytest.fixture
async def client(db_session, mock_valkey, mock_http_client):
    """
    Full FastAPI test client with:
    - In-memory SQLite DB
    - Mocked Valkey
    - Mocked HTTP client (no real LLM/STT/TTS calls)
    """
    from main import app
    from db.connection import get_db
    import cache

    # Override dependencies
    app.dependency_overrides[get_db] = lambda: db_session
    cache.valkey = mock_valkey

    # Patch app.state.http (used by sessions.py for STT/TTS/LLM)
    app.state.http = mock_http_client

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest.fixture
def demo_token():
    """Return a valid JWT for the demo user (for Authorization headers)."""
    from jwt_utils import create_access_token
    return create_access_token("d0000000-0000-0000-0000-000000000001")
