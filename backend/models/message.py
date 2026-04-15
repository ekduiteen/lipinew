from datetime import datetime, timezone
from sqlalchemy import DateTime, Float, ForeignKey, Integer, Text
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
    detected_language: Mapped[str | None] = mapped_column(Text, nullable=True)
    audio_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    audio_duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    raw_signals_json: Mapped[dict] = mapped_column(JSONB, default=dict)
    derived_signals_json: Mapped[dict] = mapped_column(JSONB, default=dict)
    high_value_signals_json: Mapped[dict] = mapped_column(JSONB, default=dict)
    style_signals_json: Mapped[dict] = mapped_column(JSONB, default=dict)
    prosody_signals_json: Mapped[dict] = mapped_column(JSONB, default=dict)
    nuance_signals_json: Mapped[dict] = mapped_column(JSONB, default=dict)

    stt_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)

    llm_model: Mapped[str | None] = mapped_column(Text, nullable=True)
    llm_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    llm_latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
