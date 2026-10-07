"""Retained refund dispatch and provider evidence, without cascade FKs or PII."""
import uuid
from datetime import datetime
from sqlalchemy import CheckConstraint, DateTime, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base


class PaymentRefund(Base):
    __tablename__ = "payment_refunds"
    __table_args__ = (
        UniqueConstraint("mode", "account_id", "payment_id", name="uq_refund_dispatch_payment"),
        CheckConstraint("mode = 'test' AND currency = 'INR' AND amount_minor >= 100", name="ck_refund_dispatch_scope"),
        CheckConstraint("state IN ('sending','uncertain','pending','processed','failed','external')", name="ck_refund_dispatch_state"),
        CheckConstraint("source_kind IN ('activation','renewal')", name="ck_refund_dispatch_source"),
    )
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(nullable=False, index=True)
    source_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    source_kind: Mapped[str] = mapped_column(String(16), nullable=False)
    mode: Mapped[str] = mapped_column(String(4), nullable=False)
    account_id: Mapped[str] = mapped_column(String(68), nullable=False)
    provider_key_id: Mapped[str] = mapped_column(String(100), nullable=False)
    payment_id: Mapped[str] = mapped_column(String(104), nullable=False)
    amount_minor: Mapped[int] = mapped_column(Integer, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    operator_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    evidence_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    state: Mapped[str] = mapped_column(String(16), nullable=False)
    requested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    refund_id: Mapped[str | None] = mapped_column(String(104), nullable=True)


class RefundObservation(Base):
    __tablename__ = "refund_observations"
    __table_args__ = (
        UniqueConstraint("mode", "account_id", "refund_id", name="uq_refund_observation_identity"),
        CheckConstraint("mode = 'test' AND currency = 'INR' AND amount_minor > 0", name="ck_refund_observation_scope"),
        CheckConstraint("state IN ('pending','processed','failed')", name="ck_refund_observation_state"),
    )
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(nullable=False, index=True)
    mode: Mapped[str] = mapped_column(String(4), nullable=False)
    account_id: Mapped[str] = mapped_column(String(68), nullable=False)
    payment_id: Mapped[str] = mapped_column(String(104), nullable=False)
    refund_id: Mapped[str] = mapped_column(String(104), nullable=False)
    amount_minor: Mapped[int] = mapped_column(Integer, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    state: Mapped[str] = mapped_column(String(16), nullable=False)
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
