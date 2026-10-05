"""Minimal retained financial grant evidence; no account deletion cascade."""
import uuid
from datetime import datetime
from sqlalchemy import CheckConstraint, DateTime, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base


class PaymentActivation(Base):
    __tablename__ = "payment_activations"
    __table_args__ = (
        UniqueConstraint("provider", "mode", "account_id", "payment_id", name="uq_payment_activation_identity"),
        UniqueConstraint("reservation_id", name="uq_payment_activation_reservation"),
        CheckConstraint("provider = 'razorpay'", name="ck_payment_activation_provider"),
        CheckConstraint("mode IN ('test','live')", name="ck_payment_activation_mode"),
        CheckConstraint("plan IN ('pro','max')", name="ck_payment_activation_plan"),
        CheckConstraint("billing_interval IN ('monthly','annual')", name="ck_payment_activation_interval"),
        CheckConstraint("amount_minor > 0 AND currency = 'INR'", name="ck_payment_activation_amount"),
        CheckConstraint("period_end > period_start", name="ck_payment_activation_period"),
    )
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    provider: Mapped[str] = mapped_column(String(16), nullable=False)
    mode: Mapped[str] = mapped_column(String(4), nullable=False)
    account_id: Mapped[str] = mapped_column(String(68), nullable=False)
    provider_key_id: Mapped[str] = mapped_column(String(100), nullable=False)
    payment_id: Mapped[str] = mapped_column(String(104), nullable=False)
    order_id: Mapped[str] = mapped_column(String(106), nullable=False)
    reservation_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    user_id: Mapped[uuid.UUID] = mapped_column(nullable=False, index=True)
    source_event_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    plan: Mapped[str] = mapped_column(String(16), nullable=False)
    billing_interval: Mapped[str] = mapped_column(String(16), nullable=False)
    amount_minor: Mapped[int] = mapped_column(Integer, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    period_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    period_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    applied_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
