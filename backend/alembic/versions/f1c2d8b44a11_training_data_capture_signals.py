"""training_data_capture_signals

Revision ID: f1c2d8b44a11
Revises: e4b7f9a21c10
Create Date: 2026-04-16 16:30:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "f1c2d8b44a11"
down_revision = "e4b7f9a21c10"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "messages",
        sa.Column("raw_signals_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
    )
    op.add_column(
        "messages",
        sa.Column("derived_signals_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
    )
    op.add_column(
        "messages",
        sa.Column("high_value_signals_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
    )
    op.add_column(
        "messages",
        sa.Column("style_signals_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
    )
    op.add_column(
        "messages",
        sa.Column("prosody_signals_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
    )
    op.add_column(
        "messages",
        sa.Column("nuance_signals_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
    )

    op.add_column(
        "session_memory_snapshots",
        sa.Column("style_memory_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
    )

    op.create_table(
        "teacher_signals",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column("teacher_id", postgresql.UUID(as_uuid=False), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("session_id", postgresql.UUID(as_uuid=False), sa.ForeignKey("teaching_sessions.id", ondelete="SET NULL"), nullable=True),
        sa.Column("message_id", postgresql.UUID(as_uuid=False), sa.ForeignKey("messages.id", ondelete="SET NULL"), nullable=True),
        sa.Column("signal_type", sa.Text(), nullable=False),
        sa.Column("signal_key", sa.Text(), nullable=False),
        sa.Column("signal_value_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("confidence", sa.Float(), nullable=False, server_default="0.5"),
        sa.Column("source", sa.Text(), nullable=False, server_default="input_understanding_v1"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
    )
    op.create_index("idx_teacher_signals_teacher_created", "teacher_signals", ["teacher_id", "created_at"])
    op.create_index("idx_teacher_signals_type_key", "teacher_signals", ["signal_type", "signal_key"])


def downgrade() -> None:
    op.drop_index("idx_teacher_signals_type_key", table_name="teacher_signals")
    op.drop_index("idx_teacher_signals_teacher_created", table_name="teacher_signals")
    op.drop_table("teacher_signals")

    op.drop_column("session_memory_snapshots", "style_memory_json")

    op.drop_column("messages", "nuance_signals_json")
    op.drop_column("messages", "prosody_signals_json")
    op.drop_column("messages", "style_signals_json")
    op.drop_column("messages", "high_value_signals_json")
    op.drop_column("messages", "derived_signals_json")
    op.drop_column("messages", "raw_signals_json")
