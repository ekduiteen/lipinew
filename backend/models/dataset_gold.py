from datetime import datetime, timezone
import uuid
from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column
from .base import Base

class GoldRecord(Base):
    """
    The 'Gold Standard' record. 
    Snapshotted from the raw message history once human-labeled.
    Used as the definitive source for model training.
    """
    __tablename__ = "dataset_gold_records"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # Links to original raw data (kept for provenance)
    original_message_id: Mapped[str | None] = mapped_column(UUID(as_uuid=False), ForeignKey("messages.id", ondelete="SET NULL"), nullable=True)
    session_id: Mapped[str | None] = mapped_column(UUID(as_uuid=False), ForeignKey("teaching_sessions.id", ondelete="SET NULL"), nullable=True)
    teacher_id: Mapped[str | None] = mapped_column(UUID(as_uuid=False), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    
    # Ground Truth Content
    audio_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    raw_transcript: Mapped[str] = mapped_column(Text) # The STT output
    corrected_transcript: Mapped[str] = mapped_column(Text) # The Human-corrected version
    
    # Linguistic Metadata
    dialect: Mapped[str | None] = mapped_column(String, nullable=True, index=True)
    register: Mapped[str | None] = mapped_column(String, nullable=True) # Tapai, Timi, etc.
    primary_language: Mapped[str] = mapped_column(String, default="ne")
    tags: Mapped[list] = mapped_column(JSONB, default=list) # e.g., ["nursery_rhyme", "slang", "high_code_switch"]

    # Quality & Acoustic Metrics
    audio_quality_score: Mapped[float] = mapped_column(Float, default=1.0) # 0.0 to 1.0 (Moderator rated)
    noise_level: Mapped[str | None] = mapped_column(String, nullable=True) # low, medium, high
    
    # Metadata
    labeled_by: Mapped[str | None] = mapped_column(UUID(as_uuid=False), ForeignKey("admin_accounts.id", ondelete="SET NULL"), nullable=True)
    is_published: Mapped[bool] = mapped_column(Boolean, default=True) # Whether it should be included in new exports
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc)
    )

class DatasetSnapshot(Base):
    """
    A versioned 'release' of the Gold data ready for training. (e.g., 'v1-ne-ktm-stt')
    """
    __tablename__ = "dataset_snapshots"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4()))
    dataset_name: Mapped[str] = mapped_column(String, index=True)
    version: Mapped[str] = mapped_column(String) # e.g., "1.0.0"
    
    record_count: Mapped[int] = mapped_column(Integer, default=0)
    filter_query: Mapped[dict] = mapped_column(JSONB, default=dict) # The criteria used to build this snapshot
    
    download_url: Mapped[str | None] = mapped_column(Text, nullable=True) # Path to ZIP/JSONL in MinIO
    
    created_by: Mapped[str | None] = mapped_column(UUID(as_uuid=False), ForeignKey("admin_accounts.id", ondelete="SET NULL"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
