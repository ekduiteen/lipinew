from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class CorrectionEvent(Base):
    __tablename__ = "correction_events"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True)
    session_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("teaching_sessions.id", ondelete="CASCADE")
    )
    teacher_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("users.id", ondelete="CASCADE")
    )
    wrong_message_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False), ForeignKey("messages.id", ondelete="SET NULL"), nullable=True
    )
    correction_message_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("messages.id", ondelete="CASCADE")
    )
    wrong_claim: Mapped[str] = mapped_column(Text)
    corrected_claim: Mapped[str] = mapped_column(Text)
    correction_type: Mapped[str] = mapped_column(Text, default="direct_correction")
    confidence_before: Mapped[float | None] = mapped_column(Float, nullable=True)
    confidence_after: Mapped[float | None] = mapped_column(Float, nullable=True)
    topic: Mapped[str | None] = mapped_column(Text, nullable=True)
    language_key: Mapped[str] = mapped_column(Text, default="ne")
    source_audio_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_approved: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )


class SessionMemorySnapshot(Base):
    __tablename__ = "session_memory_snapshots"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True)
    session_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("teaching_sessions.id", ondelete="CASCADE")
    )
    teacher_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("users.id", ondelete="CASCADE")
    )
    turn_index: Mapped[int] = mapped_column(Integer, default=0)
    active_language: Mapped[str | None] = mapped_column(Text, nullable=True)
    active_topic: Mapped[str | None] = mapped_column(Text, nullable=True)
    recent_taught_words: Mapped[list] = mapped_column(JSONB, default=list)
    recent_corrections: Mapped[list] = mapped_column(JSONB, default=list)
    unresolved_misunderstandings: Mapped[list] = mapped_column(JSONB, default=list)
    next_followup_goal: Mapped[str | None] = mapped_column(Text, nullable=True)
    user_style: Mapped[str] = mapped_column(Text, default="neutral")
    style_memory_json: Mapped[dict] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )


class TeacherSignal(Base):
    __tablename__ = "teacher_signals"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True)
    teacher_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("users.id", ondelete="CASCADE")
    )
    session_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False), ForeignKey("teaching_sessions.id", ondelete="SET NULL"), nullable=True
    )
    message_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False), ForeignKey("messages.id", ondelete="SET NULL"), nullable=True
    )
    signal_type: Mapped[str] = mapped_column(Text)
    signal_key: Mapped[str] = mapped_column(Text)
    signal_value_json: Mapped[dict] = mapped_column(JSONB, default=dict)
    confidence: Mapped[float] = mapped_column(Float, default=0.5)
    source: Mapped[str] = mapped_column(Text, default="input_understanding_v1")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )


class TeacherCredibilityEvent(Base):
    __tablename__ = "teacher_credibility_events"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True)
    teacher_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("users.id", ondelete="CASCADE")
    )
    session_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False), ForeignKey("teaching_sessions.id", ondelete="SET NULL"), nullable=True
    )
    event_type: Mapped[str] = mapped_column(Text)
    score_delta: Mapped[float] = mapped_column(Float, default=0.0)
    resulting_score: Mapped[float] = mapped_column(Float, default=0.5)
    detail: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )


class KnowledgeConfidenceHistory(Base):
    __tablename__ = "knowledge_confidence_history"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True)
    teacher_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    session_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False), ForeignKey("teaching_sessions.id", ondelete="SET NULL"), nullable=True
    )
    correction_event_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False), ForeignKey("correction_events.id", ondelete="SET NULL"), nullable=True
    )
    knowledge_key: Mapped[str] = mapped_column(Text)
    language_key: Mapped[str] = mapped_column(Text, default="ne")
    previous_confidence: Mapped[float] = mapped_column(Float, default=0.0)
    new_confidence: Mapped[float] = mapped_column(Float, default=0.0)
    change_reason: Mapped[str] = mapped_column(Text)
    is_contradiction_hook: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )


class UsageRule(Base):
    __tablename__ = "usage_rules"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True)
    teacher_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    session_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False), ForeignKey("teaching_sessions.id", ondelete="SET NULL"), nullable=True
    )
    correction_event_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False), ForeignKey("correction_events.id", ondelete="SET NULL"), nullable=True
    )
    topic_key: Mapped[str | None] = mapped_column(Text, nullable=True)
    language_key: Mapped[str] = mapped_column(Text, default="ne")
    rule_type: Mapped[str] = mapped_column(Text, default="usage_note")
    rule_text: Mapped[str] = mapped_column(Text)
    source_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    confidence: Mapped[float] = mapped_column(Float, default=0.5)
    source_audio_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_approved: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

class ReviewQueueItem(Base):
    __tablename__ = "review_queue_items"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True)
    source_audio_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_transcript: Mapped[str | None] = mapped_column(Text, nullable=True)
    teacher_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    session_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False), ForeignKey("teaching_sessions.id", ondelete="SET NULL"), nullable=True
    )
    extracted_claim: Mapped[str] = mapped_column(Text)
    extraction_metadata: Mapped[dict] = mapped_column(JSONB, default=dict)
    confidence: Mapped[float] = mapped_column(Float, default=0.5)
    model_source: Mapped[str] = mapped_column(Text, default="gemma_audio_v1")
    status: Mapped[str] = mapped_column(Text, default="pending_review") # pending_review, approved, rejected, needs_more_context
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc)
    )


class VocabularyEntry(Base):
    __tablename__ = "vocabulary_entries"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True)
    word: Mapped[str] = mapped_column(Text)
    language: Mapped[str] = mapped_column(Text, default="ne")
    definition: Mapped[str | None] = mapped_column(Text, nullable=True)
    confidence: Mapped[float] = mapped_column(Float, default=0.0)
    times_taught: Mapped[int] = mapped_column(Integer, default=1)
    pioneer_teacher_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    distinct_teacher_count: Mapped[int] = mapped_column(Integer, default=1)
    admin_approved: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )


class VocabularyTeacher(Base):
    __tablename__ = "vocabulary_teachers"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True)
    vocabulary_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("vocabulary_entries.id", ondelete="CASCADE")
    )
    teacher_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("users.id", ondelete="CASCADE")
    )
    session_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False), ForeignKey("teaching_sessions.id", ondelete="SET NULL"), nullable=True
    )
    contribution_type: Mapped[str] = mapped_column(Text, default="reinforcement")
    confidence_added: Mapped[float] = mapped_column(Float, default=0.0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
