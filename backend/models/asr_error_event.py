from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class ASRErrorEvent(Base):
    __tablename__ = "asr_error_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    message_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False), ForeignKey("messages.id", ondelete="CASCADE"), nullable=True
    )
    teacher_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    country_code: Mapped[str | None] = mapped_column(String(10), nullable=True)
    target_language: Mapped[str | None] = mapped_column(String(50), nullable=True, index=True)
    base_asr_languages: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    script: Mapped[str | None] = mapped_column(String(50), nullable=True)
    raw_stt: Mapped[str | None] = mapped_column(Text, nullable=True)
    teacher_correction: Mapped[str | None] = mapped_column(Text, nullable=True)
    error_type: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    error_family: Mapped[str | None] = mapped_column(String(100), nullable=True)
    severity: Mapped[str | None] = mapped_column(String(20), nullable=True)
    start_char: Mapped[int | None] = mapped_column(Integer, nullable=True)
    end_char: Mapped[int | None] = mapped_column(Integer, nullable=True)
    audio_quality: Mapped[float | None] = mapped_column(Float, nullable=True)
    stt_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    teacher_verified: Mapped[bool] = mapped_column(Boolean, default=True)
    training_tier: Mapped[str | None] = mapped_column(String(20), nullable=True)
    metadata_json: Mapped[dict] = mapped_column("metadata", JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True
    )
