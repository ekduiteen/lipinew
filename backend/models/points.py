from datetime import date, datetime, timezone
from sqlalchemy import Boolean, Date, DateTime, Float, ForeignKey, Integer, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column
from .base import Base


class PointsTransaction(Base):
    """Immutable append-only points event log. Never update, never delete."""
    __tablename__ = "points_transactions"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True)
    teacher_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("users.id", ondelete="CASCADE")
    )
    session_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("teaching_sessions.id", ondelete="SET NULL"),
        nullable=True,
    )
    event_type: Mapped[str] = mapped_column(Text)
    base_points: Mapped[int] = mapped_column(Integer)
    multiplier: Mapped[float] = mapped_column(Float, default=1.0)
    final_points: Mapped[int] = mapped_column(Integer)
    context: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    validated: Mapped[bool] = mapped_column(Boolean, default=False)
    validation_method: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )


class TeacherPointsSummary(Base):
    """Cached totals rebuilt from transactions every 5 min."""
    __tablename__ = "teacher_points_summary"

    teacher_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    total_points: Mapped[int] = mapped_column(Integer, default=0)
    total_words_taught: Mapped[int] = mapped_column(Integer, default=0)
    total_corrections: Mapped[int] = mapped_column(Integer, default=0)
    total_sessions: Mapped[int] = mapped_column(Integer, default=0)
    total_minutes: Mapped[int] = mapped_column(Integer, default=0)
    current_streak_days: Mapped[int] = mapped_column(Integer, default=0)
    longest_streak_days: Mapped[int] = mapped_column(Integer, default=0)
    last_session_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    points_this_week: Mapped[int] = mapped_column(Integer, default=0)
    points_this_month: Mapped[int] = mapped_column(Integer, default=0)
    week_start: Mapped[date] = mapped_column(Date, default=date.today)
    month_start: Mapped[date] = mapped_column(Date, default=date.today)
    last_rebuilt: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    # ── Shims so existing code keeps working ──────────────────────────────────
    @property
    def user_id(self) -> str:
        return self.teacher_id

    @property
    def weekly_points(self) -> int:
        return self.points_this_week

    @property
    def monthly_points(self) -> int:
        return self.points_this_month

    @property
    def sessions_completed(self) -> int:
        return self.total_sessions

    @property
    def words_taught(self) -> int:
        return self.total_words_taught

    @property
    def current_streak(self) -> int:
        return self.current_streak_days

    @property
    def longest_streak(self) -> int:
        return self.longest_streak_days
