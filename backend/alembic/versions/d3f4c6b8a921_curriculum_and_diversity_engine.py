"""curriculum_and_diversity_engine

Revision ID: d3f4c6b8a921
Revises: 91ba4c4fe766
Create Date: 2026-04-15 13:00:00.000000
"""

from __future__ import annotations

from datetime import datetime, timezone
import uuid

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from services.curriculum import TOPIC_TAXONOMY
from services.curriculum_seed import SEED_LANGUAGES, SEED_REGISTERS


# revision identifiers, used by Alembic.
revision = "d3f4c6b8a921"
down_revision = "91ba4c4fe766"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "user_curriculum_profiles",
        sa.Column("user_id", postgresql.UUID(as_uuid=False), sa.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("primary_language", sa.Text(), nullable=False, server_default="ne"),
        sa.Column("active_register", sa.Text(), nullable=False, server_default="tapai"),
        sa.Column("code_switch_tendency", sa.Float(), nullable=False, server_default="0.1"),
        sa.Column("comfort_level", sa.Float(), nullable=False, server_default="0.5"),
        sa.Column("assigned_lane", sa.Text(), nullable=False, server_default="basics_lane"),
        sa.Column("last_topic", sa.Text(), nullable=True),
        sa.Column("last_question_type", sa.Text(), nullable=True),
        sa.Column("conversation_turn_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("correction_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
    )

    op.create_table(
        "user_topic_coverage",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=False), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("topic_key", sa.Text(), nullable=False),
        sa.Column("times_asked", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("times_answered", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("times_corrected", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("confidence_score", sa.Float(), nullable=False, server_default="0.5"),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.UniqueConstraint("user_id", "topic_key", name="uq_user_topic_coverage"),
    )
    op.create_index("idx_user_topic_coverage_user", "user_topic_coverage", ["user_id"])
    op.create_index("idx_user_topic_coverage_topic", "user_topic_coverage", ["topic_key"])

    op.create_table(
        "global_language_coverage",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column("topic_key", sa.Text(), nullable=False),
        sa.Column("register_key", sa.Text(), nullable=False),
        sa.Column("language_key", sa.Text(), nullable=False),
        sa.Column("coverage_score", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("unique_user_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("correction_density", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("last_updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.UniqueConstraint(
            "topic_key",
            "register_key",
            "language_key",
            name="uq_global_language_coverage_triplet",
        ),
    )
    op.create_index("idx_global_coverage_topic", "global_language_coverage", ["topic_key"])
    op.create_index("idx_global_coverage_register", "global_language_coverage", ["register_key"])
    op.create_index("idx_global_coverage_language", "global_language_coverage", ["language_key"])

    op.create_table(
        "curriculum_prompt_events",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=False), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("session_id", postgresql.UUID(as_uuid=False), sa.ForeignKey("teaching_sessions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("topic_key", sa.Text(), nullable=False),
        sa.Column("question_type", sa.Text(), nullable=False),
        sa.Column("register_key", sa.Text(), nullable=False),
        sa.Column("language_key", sa.Text(), nullable=False, server_default="ne"),
        sa.Column("assigned_lane", sa.Text(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("priority_score", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("fallback_question_type", sa.Text(), nullable=True),
        sa.Column("was_answered", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("was_corrected", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("response_quality", sa.Numeric(4, 3), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("answered_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("idx_curriculum_events_user_created", "curriculum_prompt_events", ["user_id", "created_at"])
    op.create_index("idx_curriculum_events_topic", "curriculum_prompt_events", ["topic_key"])
    op.create_index("idx_curriculum_events_lane", "curriculum_prompt_events", ["assigned_lane"])

    coverage_table = sa.table(
        "global_language_coverage",
        sa.column("id", postgresql.UUID(as_uuid=False)),
        sa.column("topic_key", sa.Text()),
        sa.column("register_key", sa.Text()),
        sa.column("language_key", sa.Text()),
        sa.column("coverage_score", sa.Float()),
        sa.column("unique_user_count", sa.Integer()),
        sa.column("correction_density", sa.Float()),
        sa.column("last_updated_at", sa.DateTime(timezone=True)),
    )
    now = datetime.now(timezone.utc)
    seed_rows = []
    for topic_key in TOPIC_TAXONOMY:
        for register_key in SEED_REGISTERS:
            for language_key in SEED_LANGUAGES:
                seed_rows.append(
                    {
                        "id": str(uuid.uuid4()),
                        "topic_key": topic_key,
                        "register_key": register_key,
                        "language_key": language_key,
                        "coverage_score": 0.0,
                        "unique_user_count": 0,
                        "correction_density": 0.0,
                        "last_updated_at": now,
                    }
                )
    op.bulk_insert(coverage_table, seed_rows)


def downgrade() -> None:
    op.drop_index("idx_curriculum_events_lane", table_name="curriculum_prompt_events")
    op.drop_index("idx_curriculum_events_topic", table_name="curriculum_prompt_events")
    op.drop_index("idx_curriculum_events_user_created", table_name="curriculum_prompt_events")
    op.drop_table("curriculum_prompt_events")

    op.drop_index("idx_global_coverage_language", table_name="global_language_coverage")
    op.drop_index("idx_global_coverage_register", table_name="global_language_coverage")
    op.drop_index("idx_global_coverage_topic", table_name="global_language_coverage")
    op.drop_table("global_language_coverage")

    op.drop_index("idx_user_topic_coverage_topic", table_name="user_topic_coverage")
    op.drop_index("idx_user_topic_coverage_user", table_name="user_topic_coverage")
    op.drop_table("user_topic_coverage")

    op.drop_table("user_curriculum_profiles")
