"""Stable external IdP identity -> original FinCo-Pilot internal UUID.

This table does not authenticate users by itself. Never infer a link by email.
"""
import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class ExternalAuthIdentity(Base):
    __tablename__ = "external_auth_identities"
    __table_args__ = (
        UniqueConstraint("provider", "issuer", "provider_subject", name="uq_external_auth_identity"),
        UniqueConstraint("provider", "issuer", "user_id", name="uq_external_auth_user"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    provider: Mapped[str] = mapped_column(String(32), nullable=False)
    issuer: Mapped[str] = mapped_column(String(255), nullable=False)
    provider_subject: Mapped[str] = mapped_column(String(255), nullable=False)
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )
