from datetime import datetime, timezone

from sqlalchemy import DateTime, Float, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class TrainingExport(Base):
    __tablename__ = "training_exports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    country_code: Mapped[str | None] = mapped_column(String(10), nullable=True)
    target_language: Mapped[str | None] = mapped_column(String(50), nullable=True)
    export_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    export_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    sample_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    total_audio_seconds: Mapped[float | None] = mapped_column(Float, nullable=True)
    metadata_json: Mapped[dict] = mapped_column("metadata", JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
