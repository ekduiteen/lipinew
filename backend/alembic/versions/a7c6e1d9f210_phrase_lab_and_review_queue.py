"""phrase_lab_and_review_queue

Revision ID: a7c6e1d9f210
Revises: f1c2d8b44a11
Create Date: 2026-04-16 23:30:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "a7c6e1d9f210"
down_revision = "f1c2d8b44a11"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("correction_events", sa.Column("source_audio_path", sa.Text(), nullable=True))
    op.add_column(
        "correction_events",
        sa.Column("is_approved", sa.Boolean(), nullable=False, server_default=sa.false()),
    )

    op.add_column("usage_rules", sa.Column("source_audio_path", sa.Text(), nullable=True))
    op.add_column(
        "usage_rules",
        sa.Column("is_approved", sa.Boolean(), nullable=False, server_default=sa.false()),
    )

    op.create_table(
        "review_queue_items",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column("source_audio_path", sa.Text(), nullable=True),
        sa.Column("source_transcript", sa.Text(), nullable=True),
        sa.Column("teacher_id", postgresql.UUID(as_uuid=False), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("session_id", postgresql.UUID(as_uuid=False), sa.ForeignKey("teaching_sessions.id", ondelete="SET NULL"), nullable=True),
        sa.Column("extracted_claim", sa.Text(), nullable=False),
        sa.Column("extraction_metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("confidence", sa.Float(), nullable=False, server_default="0.5"),
        sa.Column("model_source", sa.Text(), nullable=False, server_default="gemma_audio_v1"),
        sa.Column("status", sa.Text(), nullable=False, server_default="pending_review"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
    )

    op.create_table(
        "phrase_generation_batches",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column("generator_model", sa.Text(), nullable=False),
        sa.Column("generation_prompt", sa.Text(), nullable=False),
        sa.Column("category", sa.Text(), nullable=True),
        sa.Column("difficulty", sa.Text(), nullable=True),
        sa.Column("target_data_type", sa.Text(), nullable=True),
        sa.Column("batch_metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
    )

    op.create_table(
        "phrases",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column("text_en", sa.Text(), nullable=False),
        sa.Column("text_ne", sa.Text(), nullable=False),
        sa.Column("text_source_language", sa.Text(), nullable=False, server_default="en"),
        sa.Column("category", sa.Text(), nullable=True),
        sa.Column("difficulty", sa.Text(), nullable=True),
        sa.Column("target_data_type", sa.Text(), nullable=True),
        sa.Column("tags", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_by", sa.Text(), nullable=True),
        sa.Column("generation_batch_id", postgresql.UUID(as_uuid=False), sa.ForeignKey("phrase_generation_batches.id", ondelete="SET NULL"), nullable=True),
        sa.Column("review_status", sa.Text(), nullable=False, server_default="pending_review"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
    )

    op.create_table(
        "phrase_submission_groups",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column("phrase_id", postgresql.UUID(as_uuid=False), sa.ForeignKey("phrases.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=False), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("session_id", postgresql.UUID(as_uuid=False), sa.ForeignKey("teaching_sessions.id", ondelete="SET NULL"), nullable=True),
        sa.Column("status", sa.Text(), nullable=False, server_default="started"),
        sa.Column("skipped", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("requires_reconfirmation", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("reconfirmation_status", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
    )

    op.create_table(
        "phrase_submissions",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column("group_id", postgresql.UUID(as_uuid=False), sa.ForeignKey("phrase_submission_groups.id", ondelete="CASCADE"), nullable=False),
        sa.Column("phrase_id", postgresql.UUID(as_uuid=False), sa.ForeignKey("phrases.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=False), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("session_id", postgresql.UUID(as_uuid=False), sa.ForeignKey("teaching_sessions.id", ondelete="SET NULL"), nullable=True),
        sa.Column("audio_uri", sa.Text(), nullable=True),
        sa.Column("transcript_text", sa.Text(), nullable=True),
        sa.Column("submission_role", sa.Text(), nullable=False, server_default="primary"),
        sa.Column("variation_type", sa.Text(), nullable=True),
        sa.Column("register_label", sa.Text(), nullable=True),
        sa.Column("politeness_level", sa.Text(), nullable=True),
        sa.Column("primary_language", sa.Text(), nullable=True),
        sa.Column("secondary_languages", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("code_switch_ratio", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("tone", sa.Text(), nullable=True),
        sa.Column("emotion", sa.Text(), nullable=True),
        sa.Column("dialect_guess", sa.Text(), nullable=True),
        sa.Column("dialect_confidence", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("speech_rate", sa.Text(), nullable=True),
        sa.Column("prosody_pattern", sa.Text(), nullable=True),
        sa.Column("pronunciation_style", sa.Text(), nullable=True),
        sa.Column("stt_confidence", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("hearing_quality_label", sa.Text(), nullable=True),
        sa.Column("learning_allowed", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("conversation_allowed", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("is_noisy", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("is_retry", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("is_confirmed_valid", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
    )

    op.create_table(
        "phrase_skip_events",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column("phrase_id", postgresql.UUID(as_uuid=False), sa.ForeignKey("phrases.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=False), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("session_id", postgresql.UUID(as_uuid=False), sa.ForeignKey("teaching_sessions.id", ondelete="SET NULL"), nullable=True),
        sa.Column("reason_optional", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
    )

    op.create_table(
        "phrase_reconfirmation_queue",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column("phrase_id", postgresql.UUID(as_uuid=False), sa.ForeignKey("phrases.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=False), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("original_group_id", postgresql.UUID(as_uuid=False), sa.ForeignKey("phrase_submission_groups.id", ondelete="SET NULL"), nullable=True),
        sa.Column("priority_score", sa.Float(), nullable=False, server_default="50.0"),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("scheduled_after_n_prompts", sa.Integer(), nullable=False, server_default="5"),
        sa.Column("status", sa.Text(), nullable=False, server_default="pending"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
    )

    op.create_table(
        "phrase_metrics",
        sa.Column("phrase_id", postgresql.UUID(as_uuid=False), sa.ForeignKey("phrases.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("total_submissions", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("voice_submission_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("language_coverage", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("dialect_coverage", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("under_collected_flag", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("quality_score", sa.Float(), nullable=False, server_default="0.0"),
    )


def downgrade() -> None:
    op.drop_table("phrase_metrics")
    op.drop_table("phrase_reconfirmation_queue")
    op.drop_table("phrase_skip_events")
    op.drop_table("phrase_submissions")
    op.drop_table("phrase_submission_groups")
    op.drop_table("phrases")
    op.drop_table("phrase_generation_batches")
    op.drop_table("review_queue_items")

    op.drop_column("usage_rules", "is_approved")
    op.drop_column("usage_rules", "source_audio_path")
    op.drop_column("correction_events", "is_approved")
    op.drop_column("correction_events", "source_audio_path")
