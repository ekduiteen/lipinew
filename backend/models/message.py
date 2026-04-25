from datetime import datetime, timezone
from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column
from .base import Base


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True)
    session_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("teaching_sessions.id", ondelete="CASCADE")
    )
    teacher_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("users.id", ondelete="CASCADE")
    )

    turn_index: Mapped[int] = mapped_column(Integer)
    role: Mapped[str] = mapped_column(Text)      # 'teacher' | 'lipi'

    text: Mapped[str] = mapped_column(Text)
    country_code: Mapped[str | None] = mapped_column(String(10), nullable=True, index=True)
    target_language: Mapped[str | None] = mapped_column(String(50), nullable=True, index=True)
    bridge_language: Mapped[str | None] = mapped_column(String(50), nullable=True)
    script: Mapped[str | None] = mapped_column(String(50), nullable=True)
    dialect_label: Mapped[str | None] = mapped_column(String(255), nullable=True)
    detected_language: Mapped[str | None] = mapped_column(Text, nullable=True)
    selected_language: Mapped[str | None] = mapped_column(String(50), nullable=True)
    code_switch_ratio: Mapped[float | None] = mapped_column(Float, nullable=True)
    asr_drift_type: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    needs_teacher_confirmation: Mapped[bool] = mapped_column(Boolean, default=False)
    audio_quality: Mapped[float | None] = mapped_column(Float, nullable=True)
    audio_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    audio_duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    raw_signals_json: Mapped[dict] = mapped_column(JSONB, default=dict)
    derived_signals_json: Mapped[dict] = mapped_column(JSONB, default=dict)
    high_value_signals_json: Mapped[dict] = mapped_column(JSONB, default=dict)
    style_signals_json: Mapped[dict] = mapped_column(JSONB, default=dict)
    prosody_signals_json: Mapped[dict] = mapped_column(JSONB, default=dict)
    nuance_signals_json: Mapped[dict] = mapped_column(JSONB, default=dict)

    stt_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    teacher_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    raw_stt: Mapped[str | None] = mapped_column(Text, nullable=True)
    base_candidate_transcript: Mapped[str | None] = mapped_column(Text, nullable=True)
    english_candidate_transcript: Mapped[str | None] = mapped_column(Text, nullable=True)
    target_candidate_transcript: Mapped[str | None] = mapped_column(Text, nullable=True)
    acoustic_transcript: Mapped[str | None] = mapped_column(Text, nullable=True)
    normalized_transcript: Mapped[str | None] = mapped_column(Text, nullable=True)
    teacher_corrected_transcript: Mapped[str | None] = mapped_column(Text, nullable=True)
    correction_error_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    correction_error_family: Mapped[str | None] = mapped_column(String(100), nullable=True)
    training_tier: Mapped[str | None] = mapped_column(String(20), nullable=True, index=True)
    training_eligible: Mapped[bool] = mapped_column(Boolean, default=False)
    consent_training_use: Mapped[bool] = mapped_column(Boolean, default=False)

    llm_model: Mapped[str | None] = mapped_column(Text, nullable=True)
    llm_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    llm_latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
