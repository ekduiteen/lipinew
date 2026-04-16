"""heritage_sessions

Revision ID: b8d7e4c3f920
Revises: a7c6e1d9f210
Create Date: 2026-04-17 00:00:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "b8d7e4c3f920"
down_revision = "a7c6e1d9f210"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "heritage_sessions",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column(
            "teacher_id",
            postgresql.UUID(as_uuid=False),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("primary_language", sa.Text(), nullable=False, server_default="nepali"),
        sa.Column("contribution_mode", sa.Text(), nullable=False),
        sa.Column("starter_prompt", sa.Text(), nullable=False),
        sa.Column("response_text", sa.Text(), nullable=True),
        sa.Column("response_audio_url", sa.Text(), nullable=True),
        sa.Column("follow_up_prompt", sa.Text(), nullable=True),
        sa.Column("follow_up_response_text", sa.Text(), nullable=True),
        sa.Column("follow_up_response_audio", sa.Text(), nullable=True),
        sa.Column("status", sa.Text(), nullable=False, server_default="started"),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
    )


def downgrade() -> None:
    op.drop_table("heritage_sessions")
