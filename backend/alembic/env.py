"""Alembic environment — async SQLAlchemy + Pydantic settings."""

import asyncio
import sys
import os
from logging.config import fileConfig

from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from alembic import context

# Make backend package root importable when running alembic from backend/ dir
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

# Import all models so autogenerate detects every table
from models.base import Base  # noqa: F401
import models.user             # noqa: F401
import models.session          # noqa: F401
import models.message          # noqa: F401
import models.points           # noqa: F401
import models.badge            # noqa: F401
import models.curriculum       # noqa: F401
import models.asr_candidate    # noqa: F401
import models.asr_error_event  # noqa: F401
import models.text_corpus_item # noqa: F401
import models.training_export  # noqa: F401
import models.phrases          # noqa: F401
import models.heritage         # noqa: F401
import models.admin_control    # noqa: F401
import models.dataset_gold     # noqa: F401
import models.intelligence     # noqa: F401

from config import settings

# Alembic Config object
config = context.config

# Override URL with Pydantic settings value (strip +asyncpg for sync fallback)
_sync_url = settings.database_url.replace("+asyncpg", "")
config.set_main_option("sqlalchemy.url", _sync_url)

# Logging setup
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# All ORM models' metadata — used by autogenerate
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Generate SQL script without a live DB connection."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Run migrations against a live async PostgreSQL connection."""
    section = config.get_section(config.config_ini_section, {})
    # Use the asyncpg URL for the actual live connection
    section["sqlalchemy.url"] = settings.database_url

    connectable = async_engine_from_config(
        section,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


def run_migrations_online() -> None:
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
