from __future__ import annotations

import uuid
from datetime import datetime, timezone
from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID

from .base import Base
from sqlalchemy.orm import Mapped, mapped_column, relationship

class PhraseGenerationBatch(Base):
    __tablename__ = "phrase_generation_batches"
    
    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4()))
    generator_model: Mapped[str] = mapped_column(Text)
    generation_prompt: Mapped[str] = mapped_column(Text)
    category: Mapped[str | None] = mapped_column(Text, nullable=True)
    difficulty: Mapped[str | None] = mapped_column(Text, nullable=True)
    target_data_type: Mapped[str | None] = mapped_column(Text, nullable=True)
    batch_metadata: Mapped[dict] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

class Phrase(Base):
    __tablename__ = "phrases"
    
    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4()))
    text_en: Mapped[str] = mapped_column(Text)
    text_ne: Mapped[str] = mapped_column(Text)
    text_source_language: Mapped[str] = mapped_column(Text, default="en")
    category: Mapped[str | None] = mapped_column(Text, nullable=True)
    difficulty: Mapped[str | None] = mapped_column(Text, nullable=True)
    target_data_type: Mapped[str | None] = mapped_column(Text, nullable=True)
    tags: Mapped[list] = mapped_column(JSONB, default=list) # e.g., ["daily", "spoken", "basic"]
    is_active: Mapped[bool] = mapped_column(Boolean, default=False)
    created_by: Mapped[str | None] = mapped_column(Text, nullable=True) # E.g., admin id or "llm_bot"
    generation_batch_id: Mapped[str | None] = mapped_column(UUID(as_uuid=False), ForeignKey("phrase_generation_batches.id", ondelete="SET NULL"), nullable=True)
    review_status: Mapped[str] = mapped_column(Text, default="pending_review") # pending_review, approved, rejected
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

class PhraseSubmissionGroup(Base):
    __tablename__ = "phrase_submission_groups"
    
    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4()))
    phrase_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("phrases.id", ondelete="CASCADE"))
    user_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("users.id", ondelete="CASCADE"))
    session_id: Mapped[str | None] = mapped_column(UUID(as_uuid=False), ForeignKey("teaching_sessions.id", ondelete="SET NULL"), nullable=True)
    status: Mapped[str] = mapped_column(Text, default="started") # started, completed, skipped
    skipped: Mapped[bool] = mapped_column(Boolean, default=False)
    requires_reconfirmation: Mapped[bool] = mapped_column(Boolean, default=False)
    reconfirmation_status: Mapped[str | None] = mapped_column(Text, nullable=True) # None, pending, completed
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

class PhraseSubmission(Base):
    __tablename__ = "phrase_submissions"
    
    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4()))
    group_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("phrase_submission_groups.id", ondelete="CASCADE"))
    phrase_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("phrases.id", ondelete="CASCADE"))
    user_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("users.id", ondelete="CASCADE"))
    session_id: Mapped[str | None] = mapped_column(UUID(as_uuid=False), ForeignKey("teaching_sessions.id", ondelete="SET NULL"), nullable=True)
    
    audio_uri: Mapped[str | None] = mapped_column(Text, nullable=True)
    transcript_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    submission_role: Mapped[str] = mapped_column(Text, default="primary") # primary, variation, reconfirmation
    variation_type: Mapped[str | None] = mapped_column(Text, nullable=True) # casual, friendly, respectful, elder, local
    register_label: Mapped[str | None] = mapped_column(Text, nullable=True) # ta, timi, tapai, hajur
    politeness_level: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    primary_language: Mapped[str | None] = mapped_column(Text, nullable=True)
    secondary_languages: Mapped[list] = mapped_column(JSONB, default=list)
    code_switch_ratio: Mapped[float] = mapped_column(Float, default=0.0)
    
    tone: Mapped[str | None] = mapped_column(Text, nullable=True)
    emotion: Mapped[str | None] = mapped_column(Text, nullable=True)
    dialect_guess: Mapped[str | None] = mapped_column(Text, nullable=True)
    dialect_confidence: Mapped[float] = mapped_column(Float, default=0.0)
    speech_rate: Mapped[str | None] = mapped_column(Text, nullable=True)
    prosody_pattern: Mapped[str | None] = mapped_column(Text, nullable=True)
    pronunciation_style: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    stt_confidence: Mapped[float] = mapped_column(Float, default=0.0)
    hearing_quality_label: Mapped[str | None] = mapped_column(Text, nullable=True) # poor, ok, good
    learning_allowed: Mapped[bool] = mapped_column(Boolean, default=True)
    conversation_allowed: Mapped[bool] = mapped_column(Boolean, default=True)
    
    is_noisy: Mapped[bool] = mapped_column(Boolean, default=False)
    is_retry: Mapped[bool] = mapped_column(Boolean, default=False)
    is_confirmed_valid: Mapped[bool] = mapped_column(Boolean, default=True)
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

class PhraseSkipEvent(Base):
    __tablename__ = "phrase_skip_events"
    
    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4()))
    phrase_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("phrases.id", ondelete="CASCADE"))
    user_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("users.id", ondelete="CASCADE"))
    session_id: Mapped[str | None] = mapped_column(UUID(as_uuid=False), ForeignKey("teaching_sessions.id", ondelete="SET NULL"), nullable=True)
    reason_optional: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

class PhraseReconfirmationQueue(Base):
    __tablename__ = "phrase_reconfirmation_queue"
    
    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4()))
    phrase_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("phrases.id", ondelete="CASCADE"))
    user_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("users.id", ondelete="CASCADE"))
    original_group_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("phrase_submission_groups.id", ondelete="SET NULL"), nullable=True)
    priority_score: Mapped[float] = mapped_column(Float, default=50.0)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    scheduled_after_n_prompts: Mapped[int] = mapped_column(Integer, default=5)
    status: Mapped[str] = mapped_column(Text, default="pending") # pending, delivered, skipped
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

class PhraseMetrics(Base):
    __tablename__ = "phrase_metrics"
    
    phrase_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("phrases.id", ondelete="CASCADE"), primary_key=True)
    total_submissions: Mapped[int] = mapped_column(Integer, default=0)
    voice_submission_count: Mapped[int] = mapped_column(Integer, default=0)
    language_coverage: Mapped[dict] = mapped_column(JSONB, default=dict)
    dialect_coverage: Mapped[dict] = mapped_column(JSONB, default=dict)
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    under_collected_flag: Mapped[bool] = mapped_column(Boolean, default=True)
    quality_score: Mapped[float] = mapped_column(Float, default=0.0)
