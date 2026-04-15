"""initial_schema — baseline stamp

This migration is intentionally empty. It exists to establish a baseline
revision so Alembic can track future migrations from this point forward.

The database schema was previously managed by:
  - init-db.sql (PostgreSQL init script via Docker)
  - Base.metadata.create_all() in main.py

Both approaches are replaced by Alembic going forward.
Future schema changes must be created via: alembic revision --autogenerate

Revision ID: 91ba4c4fe766
Revises:
Create Date: 2026-04-15 10:17:01.518831
"""
from typing import Sequence, Union

# revision identifiers, used by Alembic.
revision: str = '91ba4c4fe766'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Baseline stamp — no operations."""
    pass


def downgrade() -> None:
    """Cannot downgrade past the baseline."""
    pass
