"""Retained minimal failure evidence; no PII, deletion cascade or provider secrets."""
import uuid
from datetime import datetime
from sqlalchemy import CheckConstraint, DateTime, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base

class PaymentRecovery(Base):
    __tablename__ = "payment_recoveries"
    __table_args__ = (
        UniqueConstraint("mandate_id", "period_start", name="uq_recovery_period"),
        UniqueConstraint("mode", "account_id", "invoice_id", name="uq_recovery_invoice"),
        CheckConstraint("mode = 'test'", name="ck_recovery_mode"),
        CheckConstraint("provider_state IN ('pending','halted')", name="ck_recovery_state"),
        CheckConstraint("period_end > period_start AND paid_through <= period_start AND grace_until >= paid_through", name="ck_recovery_period"),
    )
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(nullable=False, index=True)
    mandate_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    source_event_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    mode: Mapped[str] = mapped_column(String(4), nullable=False)
    account_id: Mapped[str] = mapped_column(String(68), nullable=False)
    invoice_id: Mapped[str] = mapped_column(String(104), nullable=False)
    provider_state: Mapped[str] = mapped_column(String(16), nullable=False)
    period_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    period_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    paid_through: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    grace_until: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
