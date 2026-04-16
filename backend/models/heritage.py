from __future__ import annotations

import uuid
from datetime import datetime, timezone
from sqlalchemy import Boolean, DateTime, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class HeritageSession(Base):
    """Heritage sessions capture targeted dialect and register data via structured prompts."""

    __tablename__ = "heritage_sessions"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    teacher_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("users.id", ondelete="CASCADE")
    )
    primary_language: Mapped[str] = mapped_column(Text, default="nepali")
    contribution_mode: Mapped[str] = mapped_column(
        Text
    )  # STORY, WORD_EXPLANATION, CULTURE, PROVERB, VARIATION
    starter_prompt: Mapped[str] = mapped_column(Text)

    response_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    response_audio_url: Mapped[str | None] = mapped_column(Text, nullable=True)

    follow_up_prompt: Mapped[str | None] = mapped_column(Text, nullable=True)
    follow_up_response_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    follow_up_response_audio: Mapped[str | None] = mapped_column(Text, nullable=True)

    status: Mapped[str] = mapped_column(
        Text, default="started"
    )  # started, primary_submitted, completed
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
