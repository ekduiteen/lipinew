from datetime import datetime, timezone
from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column
from .base import Base


class TeachingSession(Base):
    __tablename__ = "teaching_sessions"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True)
    teacher_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("users.id", ondelete="CASCADE")
    )
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    ended_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    duration_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    primary_language: Mapped[str] = mapped_column(Text, default="nepali")
    message_count: Mapped[int] = mapped_column(Integer, default=0)
    teacher_turns: Mapped[int] = mapped_column(Integer, default=0)
    lipi_turns: Mapped[int] = mapped_column(Integer, default=0)
    words_taught: Mapped[int] = mapped_column(Integer, default=0)
    corrections_made: Mapped[int] = mapped_column(Integer, default=0)
    points_earned: Mapped[int] = mapped_column(Integer, default=0)
    register_used: Mapped[str | None] = mapped_column(Text, nullable=True)
    register_overridden: Mapped[bool] = mapped_column(Boolean, default=False)
    consented_for_training: Mapped[bool] = mapped_column(Boolean, default=False)
    country_code: Mapped[str | None] = mapped_column(String(10), nullable=True, index=True)
    base_asr_languages: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    target_language: Mapped[str | None] = mapped_column(String(50), nullable=True, index=True)
    bridge_language: Mapped[str | None] = mapped_column(String(50), nullable=True)
    script: Mapped[str | None] = mapped_column(String(50), nullable=True)
    dialect_label: Mapped[str | None] = mapped_column(String(255), nullable=True)
    teaching_mode: Mapped[str | None] = mapped_column(String(100), nullable=True)
    allow_code_switching: Mapped[bool] = mapped_column(Boolean, default=True)
    consent_training_use: Mapped[bool] = mapped_column(Boolean, default=False)
    session_language_contract: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
