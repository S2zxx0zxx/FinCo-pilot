"""Minimal retained mandate/cycle evidence, without deletion cascades or PII."""
import uuid
from datetime import datetime
from sqlalchemy import CheckConstraint, DateTime, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base


class RenewalMandate(Base):
    __tablename__ = "renewal_mandates"
    __table_args__ = (
        UniqueConstraint("active_user_id", name="uq_renewal_active_user"),
        UniqueConstraint("mode", "account_id", "provider_subscription_id", name="uq_renewal_provider_subscription"),
        CheckConstraint("mode = 'test' AND currency = 'INR' AND amount_minor > 0", name="ck_renewal_scope"),
        CheckConstraint("plan IN ('pro','max') AND billing_interval IN ('monthly','annual')", name="ck_renewal_plan"),
        CheckConstraint("total_count BETWEEN 1 AND 120", name="ck_renewal_count"),
        CheckConstraint("state IN ('unstarted','creating','uncertain','ready','completed','expired')", name="ck_renewal_state"),
    )
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(nullable=False, index=True)
    active_user_id: Mapped[uuid.UUID | None] = mapped_column(nullable=True)
    activation_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    subscription_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    mode: Mapped[str] = mapped_column(String(4), nullable=False)
    account_id: Mapped[str] = mapped_column(String(68), nullable=False)
    provider_key_id: Mapped[str] = mapped_column(String(100), nullable=False)
    provider_plan_id: Mapped[str] = mapped_column(String(104), nullable=False)
    provider_subscription_id: Mapped[str | None] = mapped_column(String(104), nullable=True)
    plan: Mapped[str] = mapped_column(String(16), nullable=False)
    billing_interval: Mapped[str] = mapped_column(String(16), nullable=False)
    amount_minor: Mapped[int] = mapped_column(Integer, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    total_count: Mapped[int] = mapped_column(Integer, nullable=False)
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    requested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    state: Mapped[str] = mapped_column(String(16), nullable=False)


class RenewalCycle(Base):
    __tablename__ = "renewal_cycles"
    __table_args__ = (
        UniqueConstraint("mode", "account_id", "invoice_id", name="uq_renewal_invoice"),
        UniqueConstraint("mode", "account_id", "payment_id", name="uq_renewal_payment"),
        UniqueConstraint("mandate_id", "period_start", name="uq_renewal_cycle"),
        CheckConstraint("mode = 'test' AND currency = 'INR' AND amount_minor > 0", name="ck_renewal_cycle_scope"),
        CheckConstraint("period_end > period_start", name="ck_renewal_cycle_period"),
    )
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(nullable=False, index=True)
    mandate_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    source_event_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    mode: Mapped[str] = mapped_column(String(4), nullable=False)
    account_id: Mapped[str] = mapped_column(String(68), nullable=False)
    provider_subscription_id: Mapped[str] = mapped_column(String(104), nullable=False)
    invoice_id: Mapped[str] = mapped_column(String(104), nullable=False)
    payment_id: Mapped[str] = mapped_column(String(104), nullable=False)
    amount_minor: Mapped[int] = mapped_column(Integer, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    period_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    period_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    applied_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
