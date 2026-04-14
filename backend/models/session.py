from datetime import datetime, timezone
from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, Text
from sqlalchemy.dialects.postgresql import UUID
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
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
