from datetime import datetime, timezone
import uuid
from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column
from .base import Base

class AdminAccount(Base):
    """Isolated administrative accounts for LIPI staff."""
    __tablename__ = "admin_accounts"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4()))
    email: Mapped[str] = mapped_column(String, unique=True, index=True)
    password_hash: Mapped[str | None] = mapped_column(String, nullable=True) # For local staff login
    google_sub: Mapped[str | None] = mapped_column(String, unique=True, nullable=True)
    
    full_name: Mapped[str] = mapped_column(String)
    role: Mapped[str] = mapped_column(String, default="moderator") # super_admin, data_analyst, moderator
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

class AdminAuditLog(Base):
    """Detailed audit trail for every action taken in LIPI Control."""
    __tablename__ = "admin_audit_logs"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4()))
    admin_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("admin_accounts.id", ondelete="SET NULL"), nullable=True)
    action: Mapped[str] = mapped_column(String, index=True) # e.g., "approve_turn", "export_dataset"
    entity_type: Mapped[str | None] = mapped_column(String, nullable=True) # e.g., "GoldRecord"
    entity_id: Mapped[str | None] = mapped_column(String, nullable=True)
    
    details: Mapped[dict] = mapped_column(JSONB, default=dict)
    ip_address: Mapped[str | None] = mapped_column(String, nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
