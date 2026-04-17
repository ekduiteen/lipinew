"""admin queue claims and moderation indexes

Revision ID: e6f7a8b9c0d1
Revises: d1e2f3a4b5c6
Create Date: 2026-04-18 18:00:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


revision = "e6f7a8b9c0d1"
down_revision = "d1e2f3a4b5c6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "review_queue_items",
        sa.Column("claimed_by", UUID(as_uuid=False), nullable=True),
    )
    op.add_column(
        "review_queue_items",
        sa.Column("claimed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_review_queue_claimed_by_admin",
        "review_queue_items",
        "admin_accounts",
        ["claimed_by"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "idx_review_queue_status_created",
        "review_queue_items",
        ["status", "created_at"],
    )
    op.create_index(
        "idx_review_queue_claimed_by_claimed_at",
        "review_queue_items",
        ["claimed_by", "claimed_at"],
    )
    op.create_index(
        "idx_gold_records_language_created",
        "dataset_gold_records",
        ["primary_language", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("idx_gold_records_language_created", table_name="dataset_gold_records")
    op.drop_index("idx_review_queue_claimed_by_claimed_at", table_name="review_queue_items")
    op.drop_index("idx_review_queue_status_created", table_name="review_queue_items")
    op.drop_constraint("fk_review_queue_claimed_by_admin", "review_queue_items", type_="foreignkey")
    op.drop_column("review_queue_items", "claimed_at")
    op.drop_column("review_queue_items", "claimed_by")
