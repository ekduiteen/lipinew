"""vocabulary reliability and approval index

Revision ID: d1e2f3a4b5c6
Revises: b8d7e4c3f920
Create Date: 2026-04-17 19:00:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "d1e2f3a4b5c6"
down_revision = "b8d7e4c3f920"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "vocabulary_entries",
        sa.Column(
            "distinct_teacher_count",
            sa.Integer(),
            nullable=False,
            server_default="1",
        ),
    )
    op.add_column(
        "vocabulary_entries",
        sa.Column(
            "admin_approved",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )
    op.create_index(
        "idx_usage_rules_teacher_approved",
        "usage_rules",
        ["teacher_id", "is_approved", "created_at"],
    )

    # Backfill distinct_teacher_count from vocabulary_teachers
    op.execute(
        "UPDATE vocabulary_entries v "
        "SET distinct_teacher_count = COALESCE(("
        "    SELECT COUNT(DISTINCT teacher_id) FROM vocabulary_teachers vt "
        "    WHERE vt.vocabulary_id = v.id"
        "), 1)"
    )

    # Cap pre-existing single-teacher confidence at 0.70
    op.execute(
        "UPDATE vocabulary_entries "
        "SET confidence = LEAST(confidence, 0.70) "
        "WHERE distinct_teacher_count < 2 AND admin_approved = false"
    )


def downgrade() -> None:
    op.drop_index("idx_usage_rules_teacher_approved", table_name="usage_rules")
    op.drop_column("vocabulary_entries", "admin_approved")
    op.drop_column("vocabulary_entries", "distinct_teacher_count")
