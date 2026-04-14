"""Initialize database schema from SQLAlchemy models."""

import asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from db.connection import engine
from models.base import Base


async def init_db():
    """Create all tables from models."""
    async with engine.begin() as conn:
        # Create all tables defined in Base.metadata
        await conn.run_sync(Base.metadata.create_all)
    print("✓ Database schema initialized")


async def main():
    try:
        await init_db()
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
