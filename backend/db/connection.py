"""Async SQLAlchemy engine + session factory."""

from collections.abc import AsyncIterator
from urllib.parse import urlsplit

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from config import settings

_engine_kwargs = {
    "echo": False,
    "pool_pre_ping": True,
}

database_scheme = urlsplit(settings.database_url).scheme
is_sqlite = database_scheme.startswith("sqlite")
if not is_sqlite:
    _engine_kwargs["pool_size"] = 10
    _engine_kwargs["max_overflow"] = 20

engine = create_async_engine(settings.database_url, **_engine_kwargs)

SessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_db() -> AsyncIterator[AsyncSession]:
    async with SessionLocal() as session:
        yield session
