from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, Numeric, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class UserCurriculumProfile(Base):
    __tablename__ = "user_curriculum_profiles"

    user_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    primary_language: Mapped[str] = mapped_column(Text, default="ne")
    active_register: Mapped[str] = mapped_column(Text, default="tapai")
    code_switch_tendency: Mapped[float] = mapped_column(Float, default=0.1)
    comfort_level: Mapped[float] = mapped_column(Float, default=0.5)
    assigned_lane: Mapped[str] = mapped_column(Text, default="basics_lane")
    last_topic: Mapped[str | None] = mapped_column(Text, nullable=True)
    last_question_type: Mapped[str | None] = mapped_column(Text, nullable=True)
    conversation_turn_count: Mapped[int] = mapped_column(Integer, default=0)
    correction_count: Mapped[int] = mapped_column(Integer, default=0)
    last_updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )


class UserTopicCoverage(Base):
    __tablename__ = "user_topic_coverage"
    __table_args__ = (
        UniqueConstraint("user_id", "topic_key", name="uq_user_topic_coverage"),
    )

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True)
    user_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("users.id", ondelete="CASCADE")
    )
    topic_key: Mapped[str] = mapped_column(Text)
    times_asked: Mapped[int] = mapped_column(Integer, default=0)
    times_answered: Mapped[int] = mapped_column(Integer, default=0)
    times_corrected: Mapped[int] = mapped_column(Integer, default=0)
    confidence_score: Mapped[float] = mapped_column(Float, default=0.5)
    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )


class GlobalLanguageCoverage(Base):
    __tablename__ = "global_language_coverage"
    __table_args__ = (
        UniqueConstraint(
            "topic_key",
            "register_key",
            "language_key",
            name="uq_global_language_coverage_triplet",
        ),
    )

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True)
    topic_key: Mapped[str] = mapped_column(Text)
    register_key: Mapped[str] = mapped_column(Text)
    language_key: Mapped[str] = mapped_column(Text)
    coverage_score: Mapped[float] = mapped_column(Float, default=0.0)
    unique_user_count: Mapped[int] = mapped_column(Integer, default=0)
    correction_density: Mapped[float] = mapped_column(Float, default=0.0)
    last_updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )


class CurriculumPromptEvent(Base):
    __tablename__ = "curriculum_prompt_events"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True)
    user_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("users.id", ondelete="CASCADE")
    )
    session_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("teaching_sessions.id", ondelete="CASCADE")
    )
    topic_key: Mapped[str] = mapped_column(Text)
    question_type: Mapped[str] = mapped_column(Text)
    register_key: Mapped[str] = mapped_column(Text)
    language_key: Mapped[str] = mapped_column(Text, default="ne")
    assigned_lane: Mapped[str] = mapped_column(Text)
    reason: Mapped[str] = mapped_column(Text)
    priority_score: Mapped[float] = mapped_column(Float, default=0.0)
    fallback_question_type: Mapped[str | None] = mapped_column(Text, nullable=True)
    was_answered: Mapped[bool] = mapped_column(Boolean, default=False)
    was_corrected: Mapped[bool] = mapped_column(Boolean, default=False)
    response_quality: Mapped[float | None] = mapped_column(Numeric(4, 3), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    answered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
