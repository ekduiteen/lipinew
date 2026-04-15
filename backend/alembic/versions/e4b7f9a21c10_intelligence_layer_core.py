"""intelligence_layer_core

Revision ID: e4b7f9a21c10
Revises: d3f4c6b8a921
Create Date: 2026-04-16 09:00:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "e4b7f9a21c10"
down_revision = "d3f4c6b8a921"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "correction_events",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column("session_id", postgresql.UUID(as_uuid=False), sa.ForeignKey("teaching_sessions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("teacher_id", postgresql.UUID(as_uuid=False), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("wrong_message_id", postgresql.UUID(as_uuid=False), sa.ForeignKey("messages.id", ondelete="SET NULL"), nullable=True),
        sa.Column("correction_message_id", postgresql.UUID(as_uuid=False), sa.ForeignKey("messages.id", ondelete="CASCADE"), nullable=False),
        sa.Column("wrong_claim", sa.Text(), nullable=False),
        sa.Column("corrected_claim", sa.Text(), nullable=False),
        sa.Column("correction_type", sa.Text(), nullable=False, server_default="direct_correction"),
        sa.Column("confidence_before", sa.Float(), nullable=True),
        sa.Column("confidence_after", sa.Float(), nullable=True),
        sa.Column("topic", sa.Text(), nullable=True),
        sa.Column("language_key", sa.Text(), nullable=False, server_default="ne"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
    )
    op.create_index("idx_correction_events_teacher_created", "correction_events", ["teacher_id", "created_at"])
    op.create_index("idx_correction_events_session", "correction_events", ["session_id"])

    op.create_table(
        "session_memory_snapshots",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column("session_id", postgresql.UUID(as_uuid=False), sa.ForeignKey("teaching_sessions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("teacher_id", postgresql.UUID(as_uuid=False), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("turn_index", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("active_language", sa.Text(), nullable=True),
        sa.Column("active_topic", sa.Text(), nullable=True),
        sa.Column("recent_taught_words", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("recent_corrections", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("unresolved_misunderstandings", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("next_followup_goal", sa.Text(), nullable=True),
        sa.Column("user_style", sa.Text(), nullable=False, server_default="neutral"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
    )
    op.create_index("idx_session_memory_session_created", "session_memory_snapshots", ["session_id", "created_at"])
    op.create_index("idx_session_memory_teacher_created", "session_memory_snapshots", ["teacher_id", "created_at"])

    op.create_table(
        "teacher_credibility_events",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column("teacher_id", postgresql.UUID(as_uuid=False), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("session_id", postgresql.UUID(as_uuid=False), sa.ForeignKey("teaching_sessions.id", ondelete="SET NULL"), nullable=True),
        sa.Column("event_type", sa.Text(), nullable=False),
        sa.Column("score_delta", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("resulting_score", sa.Float(), nullable=False, server_default="0.5"),
        sa.Column("detail", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
    )
    op.create_index("idx_teacher_credibility_teacher_created", "teacher_credibility_events", ["teacher_id", "created_at"])

    op.create_table(
        "knowledge_confidence_history",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column("teacher_id", postgresql.UUID(as_uuid=False), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("session_id", postgresql.UUID(as_uuid=False), sa.ForeignKey("teaching_sessions.id", ondelete="SET NULL"), nullable=True),
        sa.Column("correction_event_id", postgresql.UUID(as_uuid=False), sa.ForeignKey("correction_events.id", ondelete="SET NULL"), nullable=True),
        sa.Column("knowledge_key", sa.Text(), nullable=False),
        sa.Column("language_key", sa.Text(), nullable=False, server_default="ne"),
        sa.Column("previous_confidence", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("new_confidence", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("change_reason", sa.Text(), nullable=False),
        sa.Column("is_contradiction_hook", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
    )
    op.create_index("idx_knowledge_confidence_key_created", "knowledge_confidence_history", ["knowledge_key", "created_at"])

    op.create_table(
        "usage_rules",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column("teacher_id", postgresql.UUID(as_uuid=False), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("session_id", postgresql.UUID(as_uuid=False), sa.ForeignKey("teaching_sessions.id", ondelete="SET NULL"), nullable=True),
        sa.Column("correction_event_id", postgresql.UUID(as_uuid=False), sa.ForeignKey("correction_events.id", ondelete="SET NULL"), nullable=True),
        sa.Column("topic_key", sa.Text(), nullable=True),
        sa.Column("language_key", sa.Text(), nullable=False, server_default="ne"),
        sa.Column("rule_type", sa.Text(), nullable=False, server_default="usage_note"),
        sa.Column("rule_text", sa.Text(), nullable=False),
        sa.Column("source_text", sa.Text(), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=False, server_default="0.5"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
    )
    op.create_index("idx_usage_rules_topic_created", "usage_rules", ["topic_key", "created_at"])


def downgrade() -> None:
    op.drop_index("idx_usage_rules_topic_created", table_name="usage_rules")
    op.drop_table("usage_rules")

    op.drop_index("idx_knowledge_confidence_key_created", table_name="knowledge_confidence_history")
    op.drop_table("knowledge_confidence_history")

    op.drop_index("idx_teacher_credibility_teacher_created", table_name="teacher_credibility_events")
    op.drop_table("teacher_credibility_events")

    op.drop_index("idx_session_memory_teacher_created", table_name="session_memory_snapshots")
    op.drop_index("idx_session_memory_session_created", table_name="session_memory_snapshots")
    op.drop_table("session_memory_snapshots")

    op.drop_index("idx_correction_events_session", table_name="correction_events")
    op.drop_index("idx_correction_events_teacher_created", table_name="correction_events")
    op.drop_table("correction_events")
