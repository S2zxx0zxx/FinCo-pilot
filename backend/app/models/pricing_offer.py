from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import (
    JSON,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.billing.offers import (
    CAMPAIGN_CODE,
    CAMPAIGN_VERSION,
    CampaignState,
    ReservationStatus,
)
from app.core.database import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class PricingCampaign(Base):
    """Mutable operational state for a code-reviewed pricing campaign.

    Prices and capacities are intentionally not stored here. They remain in the
    immutable V1 offer catalog so an admin control cannot silently change what a
    customer is charged.
    """

    __tablename__ = "pricing_campaigns"
    __table_args__ = (
        CheckConstraint("version >= 1", name="ck_pricing_campaign_version"),
    )

    code: Mapped[str] = mapped_column(
        String(40), primary_key=True, default=CAMPAIGN_CODE
    )
    state: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        default=CampaignState.SCHEDULED.value,
        server_default=CampaignState.SCHEDULED.value,
    )
    catalog_version: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        default=CAMPAIGN_VERSION,
        server_default=CAMPAIGN_VERSION,
    )
    version: Mapped[int] = mapped_column(
        Integer, nullable=False, default=1, server_default="1"
    )
    presale_starts_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    presale_ends_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    public_launch_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    updated_by_user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow, onupdate=_utcnow
    )


class CheckoutReservation(Base):
    """Server-owned immutable quote snapshot for one checkout attempt."""

    __tablename__ = "checkout_reservations"
    __table_args__ = (
        CheckConstraint("amount_minor >= 1", name="ck_checkout_reservation_amount"),
        CheckConstraint(
            "renewal_amount_minor >= 1",
            name="ck_checkout_reservation_renewal_amount",
        ),
        CheckConstraint(
            "service_period_days >= 1 AND service_period_days <= 366",
            name="ck_checkout_reservation_service_days",
        ),
        CheckConstraint(
            "founder_wave IS NULL OR founder_wave IN (1, 2)",
            name="ck_checkout_reservation_founder_wave",
        ),
        CheckConstraint(
            "founder_position IS NULL OR founder_position >= 1",
            name="ck_checkout_reservation_founder_position",
        ),
        UniqueConstraint(
            "provider_order_id", name="uq_checkout_reservation_provider_order"
        ),
        UniqueConstraint(
            "provider_payment_id", name="uq_checkout_reservation_provider_payment"
        ),
        UniqueConstraint(
            "founder_position", name="uq_checkout_reservation_founder_position"
        ),
        Index(
            "ix_checkout_reservation_user_status",
            "user_id",
            "status",
        ),
        Index(
            "ix_checkout_reservation_offer_status",
            "offer_code",
            "status",
        ),
        Index(
            "ix_checkout_reservation_expires_at",
            "expires_at",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    plan: Mapped[str] = mapped_column(String(16), nullable=False)
    billing_interval: Mapped[str] = mapped_column(String(16), nullable=False)
    offer_code: Mapped[str] = mapped_column(String(40), nullable=False)
    campaign_code: Mapped[Optional[str]] = mapped_column(String(40), nullable=True)
    campaign_version: Mapped[str] = mapped_column(
        String(16), nullable=False, default=CAMPAIGN_VERSION
    )
    founder_wave: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    founder_position: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    amount_minor: Mapped[int] = mapped_column(Integer, nullable=False)
    currency: Mapped[str] = mapped_column(
        String(3), nullable=False, default="INR", server_default="INR"
    )
    renewal_amount_minor: Mapped[int] = mapped_column(Integer, nullable=False)
    renewal_interval: Mapped[str] = mapped_column(String(16), nullable=False)
    service_period_days: Mapped[int] = mapped_column(Integer, nullable=False)
    service_starts_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default=ReservationStatus.RESERVED.value,
        server_default=ReservationStatus.RESERVED.value,
    )
    provider: Mapped[str] = mapped_column(
        String(40), nullable=False, default="razorpay", server_default="razorpay"
    )
    provider_order_id: Mapped[Optional[str]] = mapped_column(
        String(255), nullable=True
    )
    provider_payment_id: Mapped[Optional[str]] = mapped_column(
        String(255), nullable=True
    )
    reserved_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    verified_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow, onupdate=_utcnow
    )


class FoundingMember(Base):
    """Persistent recognition for a successfully captured founder purchase."""

    __tablename__ = "founding_members"
    __table_args__ = (
        CheckConstraint("wave IN (1, 2)", name="ck_founding_member_wave"),
        CheckConstraint("founder_position >= 1", name="ck_founding_member_position"),
        UniqueConstraint(
            "reservation_id", name="uq_founding_member_reservation"
        ),
        UniqueConstraint(
            "founder_position", name="uq_founding_member_position"
        ),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    wave: Mapped[int] = mapped_column(Integer, nullable=False)
    founder_position: Mapped[int] = mapped_column(Integer, nullable=False)
    offer_code: Mapped[str] = mapped_column(String(40), nullable=False)
    reservation_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("checkout_reservations.id", ondelete="RESTRICT"),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(
        String(16), nullable=False, default="active", server_default="active"
    )
    claimed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )
    revoked_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )


class PricingAuditEvent(Base):
    """Append-only operational audit trail for pricing/campaign state."""

    __tablename__ = "pricing_audit_events"
    __table_args__ = (
        Index("ix_pricing_audit_created_at", "created_at"),
        Index("ix_pricing_audit_event_type", "event_type"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    actor_user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(40), nullable=False)
    entity_id: Mapped[str] = mapped_column(String(255), nullable=False)
    payload: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )
