"""Retained cancellation dispatch evidence; no personal data or cascade FK."""
import uuid
from datetime import datetime
from sqlalchemy import CheckConstraint, DateTime, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base


class PaymentCancellation(Base):
    __tablename__ = "payment_cancellations"
    __table_args__ = (
        UniqueConstraint("mandate_id", name="uq_cancellation_mandate"),
        CheckConstraint("state IN ('sending','uncertain','confirmed')", name="ck_cancellation_state"),
        CheckConstraint("mode = 'test'", name="ck_cancellation_mode"),
    )
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(nullable=False, index=True)
    mandate_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    mode: Mapped[str] = mapped_column(String(4), nullable=False)
    account_id: Mapped[str] = mapped_column(String(68), nullable=False)
    provider_key_id: Mapped[str] = mapped_column(String(100), nullable=False)
    provider_subscription_id: Mapped[str] = mapped_column(String(104), nullable=False)
    state: Mapped[str] = mapped_column(String(16), nullable=False)
    requested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
