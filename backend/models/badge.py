from datetime import datetime, timezone
from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from .base import Base


class Badge(Base):
    __tablename__ = "badges"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True)
    slug: Mapped[str] = mapped_column(Text, unique=True)
    name_nepali: Mapped[str] = mapped_column(Text)
    name_english: Mapped[str] = mapped_column(Text)
    description_ne: Mapped[str] = mapped_column(Text)
    description_en: Mapped[str] = mapped_column(Text)
    icon_emoji: Mapped[str] = mapped_column(Text)
    trigger_type: Mapped[str] = mapped_column(Text)   # streak_days | words_taught | corrections_made | pioneer
    trigger_value: Mapped[int | None] = mapped_column(Integer, nullable=True)
    bonus_points: Mapped[int] = mapped_column(Integer, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class TeacherBadge(Base):
    __tablename__ = "teacher_badges"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True)
    teacher_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("users.id", ondelete="CASCADE")
    )
    badge_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("badges.id", ondelete="CASCADE")
    )
    earned_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    session_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("teaching_sessions.id", ondelete="SET NULL"),
        nullable=True,
    )
    notified: Mapped[bool] = mapped_column(Boolean, default=False)

    # ── Shim so existing code using awarded_at keeps working ─────────────────
    @property
    def awarded_at(self) -> datetime:
        return self.earned_at
