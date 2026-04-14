from datetime import datetime, timezone
from sqlalchemy import Boolean, DateTime, Float, Integer, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column
from .base import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True)
    email: Mapped[str | None] = mapped_column(Text, nullable=True, unique=True)
    phone: Mapped[str | None] = mapped_column(Text, nullable=True)
    auth_provider: Mapped[str] = mapped_column(Text, default="google")
    auth_provider_id: Mapped[str | None] = mapped_column(Text, nullable=True)

    first_name: Mapped[str] = mapped_column(Text)
    last_name: Mapped[str | None] = mapped_column(Text, nullable=True)

    age: Mapped[int | None] = mapped_column(Integer, nullable=True)
    gender: Mapped[str | None] = mapped_column(Text, nullable=True)
    primary_language: Mapped[str] = mapped_column(Text, default="nepali")
    other_languages: Mapped[list] = mapped_column(JSONB, default=list)
    hometown: Mapped[str | None] = mapped_column(Text, nullable=True)
    education_level: Mapped[str | None] = mapped_column(Text, nullable=True)

    credibility_score: Mapped[float] = mapped_column(Float, default=0.5)
    troll_score: Mapped[int] = mapped_column(Integer, default=0)
    is_banned: Mapped[bool] = mapped_column(Boolean, default=False)
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False)

    consent_audio_training: Mapped[bool] = mapped_column(Boolean, default=False)
    consent_public_credit: Mapped[bool] = mapped_column(Boolean, default=False)
    consent_leaderboard_name: Mapped[bool] = mapped_column(Boolean, default=False)
    consent_dialect_training: Mapped[bool] = mapped_column(Boolean, default=False)

    onboarding_completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # ── Convenience shims so existing code keeps working ──────────────────────
    @property
    def name(self) -> str:
        """Full name as a single string (read-only helper)."""
        if self.last_name:
            return f"{self.first_name} {self.last_name}"
        return self.first_name

    @property
    def onboarding_complete(self) -> bool:
        return self.onboarding_completed_at is not None

    @onboarding_complete.setter
    def onboarding_complete(self, value: bool) -> None:
        if value and self.onboarding_completed_at is None:
            self.onboarding_completed_at = datetime.now(timezone.utc)
        elif not value:
            self.onboarding_completed_at = None

    @property
    def audio_consent(self) -> bool:
        return self.consent_audio_training

    @audio_consent.setter
    def audio_consent(self, value: bool) -> None:
        self.consent_audio_training = value

    @property
    def native_language(self) -> str:
        return self.primary_language

    @native_language.setter
    def native_language(self, value: str) -> None:
        self.primary_language = value

    @property
    def city_or_village(self) -> str | None:
        return self.hometown

    @city_or_village.setter
    def city_or_village(self, value: str | None) -> None:
        self.hometown = value
