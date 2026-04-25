"""language adaptive asr

Revision ID: a1b2c3d4e5f6
Revises: f2a3b4c5d6e7
Create Date: 2026-04-24 12:00:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID


revision = "a1b2c3d4e5f6"
down_revision = "f2a3b4c5d6e7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("teaching_sessions", sa.Column("country_code", sa.String(length=10), nullable=True))
    op.add_column("teaching_sessions", sa.Column("base_asr_languages", JSONB(astext_type=sa.Text()), nullable=True))
    op.add_column("teaching_sessions", sa.Column("target_language", sa.String(length=50), nullable=True))
    op.add_column("teaching_sessions", sa.Column("bridge_language", sa.String(length=50), nullable=True))
    op.add_column("teaching_sessions", sa.Column("script", sa.String(length=50), nullable=True))
    op.add_column("teaching_sessions", sa.Column("dialect_label", sa.String(length=255), nullable=True))
    op.add_column("teaching_sessions", sa.Column("teaching_mode", sa.String(length=100), nullable=True))
    op.add_column("teaching_sessions", sa.Column("allow_code_switching", sa.Boolean(), nullable=False, server_default=sa.true()))
    op.add_column("teaching_sessions", sa.Column("consent_training_use", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column("teaching_sessions", sa.Column("session_language_contract", JSONB(astext_type=sa.Text()), nullable=True))

    op.create_index("idx_teaching_sessions_country_target", "teaching_sessions", ["country_code", "target_language"])

    op.add_column("messages", sa.Column("country_code", sa.String(length=10), nullable=True))
    op.add_column("messages", sa.Column("target_language", sa.String(length=50), nullable=True))
    op.add_column("messages", sa.Column("bridge_language", sa.String(length=50), nullable=True))
    op.add_column("messages", sa.Column("script", sa.String(length=50), nullable=True))
    op.add_column("messages", sa.Column("dialect_label", sa.String(length=255), nullable=True))
    op.add_column("messages", sa.Column("selected_language", sa.String(length=50), nullable=True))
    op.add_column("messages", sa.Column("code_switch_ratio", sa.Float(), nullable=True))
    op.add_column("messages", sa.Column("asr_drift_type", sa.String(length=100), nullable=True))
    op.add_column("messages", sa.Column("needs_teacher_confirmation", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column("messages", sa.Column("audio_quality", sa.Float(), nullable=True))
    op.add_column("messages", sa.Column("teacher_verified", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column("messages", sa.Column("raw_stt", sa.Text(), nullable=True))
    op.add_column("messages", sa.Column("base_candidate_transcript", sa.Text(), nullable=True))
    op.add_column("messages", sa.Column("english_candidate_transcript", sa.Text(), nullable=True))
    op.add_column("messages", sa.Column("target_candidate_transcript", sa.Text(), nullable=True))
    op.add_column("messages", sa.Column("acoustic_transcript", sa.Text(), nullable=True))
    op.add_column("messages", sa.Column("normalized_transcript", sa.Text(), nullable=True))
    op.add_column("messages", sa.Column("teacher_corrected_transcript", sa.Text(), nullable=True))
    op.add_column("messages", sa.Column("correction_error_type", sa.String(length=100), nullable=True))
    op.add_column("messages", sa.Column("correction_error_family", sa.String(length=100), nullable=True))
    op.add_column("messages", sa.Column("training_tier", sa.String(length=20), nullable=True))
    op.add_column("messages", sa.Column("training_eligible", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column("messages", sa.Column("consent_training_use", sa.Boolean(), nullable=False, server_default=sa.false()))

    op.create_index("idx_messages_country_target", "messages", ["country_code", "target_language"])
    op.create_index("idx_messages_training_tier", "messages", ["training_tier"])
    op.create_index("idx_messages_asr_drift_type", "messages", ["asr_drift_type"])
    op.create_index("idx_messages_target_language", "messages", ["target_language"])

    op.create_table(
        "asr_candidates",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("message_id", UUID(as_uuid=False), sa.ForeignKey("messages.id", ondelete="CASCADE"), nullable=False),
        sa.Column("candidate_type", sa.String(length=50), nullable=False),
        sa.Column("language_code", sa.String(length=50), nullable=True),
        sa.Column("transcript", sa.Text(), nullable=True),
        sa.Column("normalized_transcript", sa.Text(), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("model_name", sa.String(length=255), nullable=True),
        sa.Column("adapter_name", sa.String(length=255), nullable=True),
        sa.Column("rank", sa.Integer(), nullable=True),
        sa.Column("selected", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("metadata", JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
    )
    op.create_index("idx_asr_candidates_message_id", "asr_candidates", ["message_id"])

    op.create_table(
        "asr_error_events",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("message_id", UUID(as_uuid=False), sa.ForeignKey("messages.id", ondelete="CASCADE"), nullable=True),
        sa.Column("teacher_id", UUID(as_uuid=False), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("country_code", sa.String(length=10), nullable=True),
        sa.Column("target_language", sa.String(length=50), nullable=True),
        sa.Column("base_asr_languages", JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("script", sa.String(length=50), nullable=True),
        sa.Column("raw_stt", sa.Text(), nullable=True),
        sa.Column("teacher_correction", sa.Text(), nullable=True),
        sa.Column("error_type", sa.String(length=100), nullable=True),
        sa.Column("error_family", sa.String(length=100), nullable=True),
        sa.Column("severity", sa.String(length=20), nullable=True),
        sa.Column("start_char", sa.Integer(), nullable=True),
        sa.Column("end_char", sa.Integer(), nullable=True),
        sa.Column("audio_quality", sa.Float(), nullable=True),
        sa.Column("stt_confidence", sa.Float(), nullable=True),
        sa.Column("teacher_verified", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("training_tier", sa.String(length=20), nullable=True),
        sa.Column("metadata", JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
    )
    op.create_index("idx_asr_error_events_target_error_type", "asr_error_events", ["target_language", "error_type"])
    op.create_index("idx_asr_error_events_country_target_created", "asr_error_events", ["country_code", "target_language", "created_at"])

    op.create_table(
        "text_corpus_items",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("teacher_id", UUID(as_uuid=False), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("country_code", sa.String(length=10), nullable=True),
        sa.Column("language_code", sa.String(length=50), nullable=True),
        sa.Column("script", sa.String(length=50), nullable=True),
        sa.Column("dialect_label", sa.String(length=255), nullable=True),
        sa.Column("source_type", sa.String(length=100), nullable=True),
        sa.Column("raw_text", sa.Text(), nullable=False),
        sa.Column("normalized_text", sa.Text(), nullable=True),
        sa.Column("romanized_text", sa.Text(), nullable=True),
        sa.Column("meaning_nepali", sa.Text(), nullable=True),
        sa.Column("meaning_english", sa.Text(), nullable=True),
        sa.Column("domain", sa.String(length=100), nullable=True),
        sa.Column("register", sa.String(length=100), nullable=True),
        sa.Column("verified", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("consent_training_use", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("metadata", JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
    )
    op.create_index("idx_text_corpus_items_language_source", "text_corpus_items", ["language_code", "source_type"])

    op.create_table(
        "training_exports",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("country_code", sa.String(length=10), nullable=True),
        sa.Column("target_language", sa.String(length=50), nullable=True),
        sa.Column("export_type", sa.String(length=50), nullable=True),
        sa.Column("export_path", sa.Text(), nullable=True),
        sa.Column("sample_count", sa.Integer(), nullable=True),
        sa.Column("total_audio_seconds", sa.Float(), nullable=True),
        sa.Column("metadata", JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
    )


def downgrade() -> None:
    op.drop_table("training_exports")

    op.drop_index("idx_text_corpus_items_language_source", table_name="text_corpus_items")
    op.drop_table("text_corpus_items")

    op.drop_index("idx_asr_error_events_country_target_created", table_name="asr_error_events")
    op.drop_index("idx_asr_error_events_target_error_type", table_name="asr_error_events")
    op.drop_table("asr_error_events")

    op.drop_index("idx_asr_candidates_message_id", table_name="asr_candidates")
    op.drop_table("asr_candidates")

    op.drop_index("idx_messages_target_language", table_name="messages")
    op.drop_index("idx_messages_asr_drift_type", table_name="messages")
    op.drop_index("idx_messages_training_tier", table_name="messages")
    op.drop_index("idx_messages_country_target", table_name="messages")
    op.drop_column("messages", "consent_training_use")
    op.drop_column("messages", "training_eligible")
    op.drop_column("messages", "training_tier")
    op.drop_column("messages", "correction_error_family")
    op.drop_column("messages", "correction_error_type")
    op.drop_column("messages", "teacher_corrected_transcript")
    op.drop_column("messages", "normalized_transcript")
    op.drop_column("messages", "acoustic_transcript")
    op.drop_column("messages", "target_candidate_transcript")
    op.drop_column("messages", "english_candidate_transcript")
    op.drop_column("messages", "base_candidate_transcript")
    op.drop_column("messages", "raw_stt")
    op.drop_column("messages", "teacher_verified")
    op.drop_column("messages", "audio_quality")
    op.drop_column("messages", "needs_teacher_confirmation")
    op.drop_column("messages", "asr_drift_type")
    op.drop_column("messages", "code_switch_ratio")
    op.drop_column("messages", "selected_language")
    op.drop_column("messages", "dialect_label")
    op.drop_column("messages", "script")
    op.drop_column("messages", "bridge_language")
    op.drop_column("messages", "target_language")
    op.drop_column("messages", "country_code")

    op.drop_index("idx_teaching_sessions_country_target", table_name="teaching_sessions")
    op.drop_column("teaching_sessions", "session_language_contract")
    op.drop_column("teaching_sessions", "consent_training_use")
    op.drop_column("teaching_sessions", "allow_code_switching")
    op.drop_column("teaching_sessions", "teaching_mode")
    op.drop_column("teaching_sessions", "dialect_label")
    op.drop_column("teaching_sessions", "script")
    op.drop_column("teaching_sessions", "bridge_language")
    op.drop_column("teaching_sessions", "target_language")
    op.drop_column("teaching_sessions", "base_asr_languages")
    op.drop_column("teaching_sessions", "country_code")
