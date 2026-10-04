"""Minimal durable provider receipts; independent of user/workspace cascades."""
import uuid
from datetime import datetime, timezone

from sqlalchemy import CheckConstraint, DateTime, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class PaymentWebhookEvent(Base):
    __tablename__ = "payment_webhook_events"
    __table_args__ = (
        UniqueConstraint("provider", "mode", "account_id", "body_sha256", name="uq_payment_webhook_body"),
        CheckConstraint("provider = 'razorpay'", name="ck_payment_webhook_provider"),
        CheckConstraint("mode IN ('test','live')", name="ck_payment_webhook_mode"),
        CheckConstraint("state IN ('pending','quarantined','processed')", name="ck_payment_webhook_state"),
        CheckConstraint("length(body_sha256) = 64", name="ck_payment_webhook_hash"),
        CheckConstraint("snapshot_ciphertext LIKE 'payment-inbox:v1:%' AND length(snapshot_ciphertext) <= 65536", name="ck_payment_webhook_ciphertext"),
    )
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    provider: Mapped[str] = mapped_column(String(16), default="razorpay")
    mode: Mapped[str] = mapped_column(String(4))
    account_id: Mapped[str] = mapped_column(String(68))
    body_sha256: Mapped[str] = mapped_column(String(64))
    event_type: Mapped[str] = mapped_column(String(128))
    # Unsigned metadata, deliberately NOT unique or authoritative.
    delivery_hint: Mapped[str | None] = mapped_column(String(128), nullable=True)
    state: Mapped[str] = mapped_column(String(16), index=True)
    snapshot_ciphertext: Mapped[str] = mapped_column(Text)
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
