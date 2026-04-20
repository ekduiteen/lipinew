"""turn intelligence layer

Revision ID: f2a3b4c5d6e7
Revises: e6f7a8b9c0d1
Create Date: 2026-04-18 22:30:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID


revision = "f2a3b4c5d6e7"
down_revision = "e6f7a8b9c0d1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "message_analysis",
        sa.Column("id", UUID(as_uuid=False), primary_key=True),
        sa.Column("message_id", UUID(as_uuid=False), sa.ForeignKey("messages.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("session_id", UUID(as_uuid=False), sa.ForeignKey("teaching_sessions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("teacher_id", UUID(as_uuid=False), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("analysis_version", sa.Text(), nullable=False, server_default="turn_intelligence_v1"),
        sa.Column("analysis_mode", sa.Text(), nullable=False, server_default="live"),
        sa.Column("primary_language", sa.Text(), nullable=True),
        sa.Column("secondary_languages", JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("transcript_original", sa.Text(), nullable=True),
        sa.Column("transcript_final", sa.Text(), nullable=True),
        sa.Column("transcript_repair_metadata", JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("intent_label", sa.Text(), nullable=False, server_default="low_signal"),
        sa.Column("intent_confidence", sa.Float(), nullable=False, server_default="0"),
        sa.Column("secondary_labels", JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("keyterms_json", JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("code_switch_json", JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("quality_json", JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("usability_score", sa.Float(), nullable=False, server_default="0"),
        sa.Column("learning_weight", sa.Float(), nullable=False, server_default="0"),
        sa.Column("model_source", sa.Text(), nullable=False, server_default="turn_intelligence_v1"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
    )
    op.create_index("idx_message_analysis_intent_created", "message_analysis", ["intent_label", "created_at"])
    op.create_index("idx_message_analysis_learning_created", "message_analysis", ["learning_weight", "created_at"])
    op.create_index("idx_message_analysis_language_created", "message_analysis", ["primary_language", "created_at"])

    op.create_table(
        "message_entities",
        sa.Column("id", UUID(as_uuid=False), primary_key=True),
        sa.Column("message_id", UUID(as_uuid=False), sa.ForeignKey("messages.id", ondelete="CASCADE"), nullable=False),
        sa.Column("session_id", UUID(as_uuid=False), sa.ForeignKey("teaching_sessions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("teacher_id", UUID(as_uuid=False), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("normalized_text", sa.Text(), nullable=False),
        sa.Column("entity_type", sa.Text(), nullable=False),
        sa.Column("language", sa.Text(), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=False, server_default="0"),
        sa.Column("source_start", sa.Integer(), nullable=True),
        sa.Column("source_end", sa.Integer(), nullable=True),
        sa.Column("attributes_json", JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
    )
    op.create_index("idx_message_entities_type_language", "message_entities", ["entity_type", "language"])
    op.create_index("idx_message_entities_norm_conf", "message_entities", ["normalized_text", "confidence"])
    op.create_index("idx_message_entities_message", "message_entities", ["message_id"])

    op.create_table(
        "admin_keyterm_seeds",
        sa.Column("id", UUID(as_uuid=False), primary_key=True),
        sa.Column("language_key", sa.Text(), nullable=False, server_default="ne"),
        sa.Column("seed_text", sa.Text(), nullable=False),
        sa.Column("normalized_text", sa.Text(), nullable=False),
        sa.Column("entity_type", sa.Text(), nullable=False, server_default="vocabulary"),
        sa.Column("domain_key", sa.Text(), nullable=True),
        sa.Column("weight", sa.Float(), nullable=False, server_default="1.0"),
        sa.Column("source_note", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_by", UUID(as_uuid=False), sa.ForeignKey("admin_accounts.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
    )
    op.create_index("idx_admin_keyterm_seeds_lang_active", "admin_keyterm_seeds", ["language_key", "is_active"])
    op.create_index("idx_admin_keyterm_seeds_norm", "admin_keyterm_seeds", ["normalized_text"])
    op.execute(
        """
        INSERT INTO admin_keyterm_seeds
            (id, language_key, seed_text, normalized_text, entity_type, domain_key, weight, source_note, is_active, created_at, updated_at)
        VALUES
            ('11111111-1111-1111-1111-111111111111', 'ne', 'तपाईं', 'तपाईं', 'honorific_or_register_term', 'register', 1.0, 'bootstrap_seed', true, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
            ('22222222-2222-2222-2222-222222222222', 'ne', 'तिमी', 'तिमी', 'honorific_or_register_term', 'register', 1.0, 'bootstrap_seed', true, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
            ('33333333-3333-3333-3333-333333333333', 'ne', 'हजुर', 'हजुर', 'honorific_or_register_term', 'register', 1.0, 'bootstrap_seed', true, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
            ('44444444-4444-4444-4444-444444444444', 'en', 'Nepali', 'nepali', 'language_name', 'language', 0.95, 'bootstrap_seed', true, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
            ('55555555-5555-5555-5555-555555555555', 'en', 'Newari', 'newari', 'language_name', 'language', 0.95, 'bootstrap_seed', true, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
            ('66666666-6666-6666-6666-666666666666', 'en', 'Maithili', 'maithili', 'language_name', 'language', 0.95, 'bootstrap_seed', true, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
        """
    )


def downgrade() -> None:
    op.drop_index("idx_admin_keyterm_seeds_norm", table_name="admin_keyterm_seeds")
    op.drop_index("idx_admin_keyterm_seeds_lang_active", table_name="admin_keyterm_seeds")
    op.drop_table("admin_keyterm_seeds")

    op.drop_index("idx_message_entities_message", table_name="message_entities")
    op.drop_index("idx_message_entities_norm_conf", table_name="message_entities")
    op.drop_index("idx_message_entities_type_language", table_name="message_entities")
    op.drop_table("message_entities")

    op.drop_index("idx_message_analysis_language_created", table_name="message_analysis")
    op.drop_index("idx_message_analysis_learning_created", table_name="message_analysis")
    op.drop_index("idx_message_analysis_intent_created", table_name="message_analysis")
    op.drop_table("message_analysis")
