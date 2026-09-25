"""Pricing founder-offer engine and audit trail.

Revision ID: 097
Revises: 096
"""

from datetime import datetime, timezone

import sqlalchemy as sa
from alembic import op

revision = "097"
down_revision = "096"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "pricing_campaigns",
        sa.Column("code", sa.String(40), primary_key=True),
        sa.Column("state", sa.String(16), nullable=False, server_default="scheduled"),
        sa.Column("catalog_version", sa.String(16), nullable=False, server_default="v1"),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("presale_starts_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("presale_ends_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("public_launch_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "updated_by_user_id",
            sa.Uuid(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.CheckConstraint("version >= 1", name="ck_pricing_campaign_version"),
    )

    op.create_table(
        "checkout_reservations",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "user_id",
            sa.Uuid(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("plan", sa.String(16), nullable=False),
        sa.Column("billing_interval", sa.String(16), nullable=False),
        sa.Column("offer_code", sa.String(40), nullable=False),
        sa.Column("campaign_code", sa.String(40), nullable=True),
        sa.Column("campaign_version", sa.String(16), nullable=False),
        sa.Column("founder_wave", sa.Integer(), nullable=True),
        sa.Column("founder_position", sa.Integer(), nullable=True),
        sa.Column("amount_minor", sa.Integer(), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False, server_default="INR"),
        sa.Column("renewal_amount_minor", sa.Integer(), nullable=False),
        sa.Column("renewal_interval", sa.String(16), nullable=False),
        sa.Column("service_period_days", sa.Integer(), nullable=False),
        sa.Column("service_starts_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="reserved"),
        sa.Column("provider", sa.String(40), nullable=False, server_default="razorpay"),
        sa.Column("provider_order_id", sa.String(255), nullable=True),
        sa.Column("provider_payment_id", sa.String(255), nullable=True),
        sa.Column(
            "reserved_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.CheckConstraint(
            "amount_minor >= 1", name="ck_checkout_reservation_amount"
        ),
        sa.CheckConstraint(
            "renewal_amount_minor >= 1",
            name="ck_checkout_reservation_renewal_amount",
        ),
        sa.CheckConstraint(
            "service_period_days >= 1 AND service_period_days <= 366",
            name="ck_checkout_reservation_service_days",
        ),
        sa.CheckConstraint(
            "founder_wave IS NULL OR founder_wave IN (1, 2)",
            name="ck_checkout_reservation_founder_wave",
        ),
        sa.CheckConstraint(
            "founder_position IS NULL OR founder_position >= 1",
            name="ck_checkout_reservation_founder_position",
        ),
        sa.UniqueConstraint(
            "provider_order_id", name="uq_checkout_reservation_provider_order"
        ),
        sa.UniqueConstraint(
            "provider_payment_id", name="uq_checkout_reservation_provider_payment"
        ),
        sa.UniqueConstraint(
            "founder_position", name="uq_checkout_reservation_founder_position"
        ),
    )
    op.create_index(
        "ix_checkout_reservation_user_status",
        "checkout_reservations",
        ["user_id", "status"],
    )
    op.create_index(
        "ix_checkout_reservation_offer_status",
        "checkout_reservations",
        ["offer_code", "status"],
    )
    op.create_index(
        "ix_checkout_reservation_expires_at",
        "checkout_reservations",
        ["expires_at"],
    )

    op.create_table(
        "founding_members",
        sa.Column(
            "user_id",
            sa.Uuid(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("wave", sa.Integer(), nullable=False),
        sa.Column("founder_position", sa.Integer(), nullable=False),
        sa.Column("offer_code", sa.String(40), nullable=False),
        sa.Column(
            "reservation_id",
            sa.Uuid(),
            sa.ForeignKey("checkout_reservations.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("status", sa.String(16), nullable=False, server_default="active"),
        sa.Column(
            "claimed_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("wave IN (1, 2)", name="ck_founding_member_wave"),
        sa.CheckConstraint(
            "founder_position >= 1", name="ck_founding_member_position"
        ),
        sa.UniqueConstraint(
            "reservation_id", name="uq_founding_member_reservation"
        ),
        sa.UniqueConstraint(
            "founder_position", name="uq_founding_member_position"
        ),
    )

    op.create_table(
        "pricing_audit_events",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "actor_user_id",
            sa.Uuid(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("event_type", sa.String(64), nullable=False),
        sa.Column("entity_type", sa.String(40), nullable=False),
        sa.Column("entity_id", sa.String(255), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index(
        "ix_pricing_audit_created_at", "pricing_audit_events", ["created_at"]
    )
    op.create_index(
        "ix_pricing_audit_event_type", "pricing_audit_events", ["event_type"]
    )

    now = datetime.now(timezone.utc)
    campaign = sa.table(
        "pricing_campaigns",
        sa.column("code", sa.String()),
        sa.column("state", sa.String()),
        sa.column("catalog_version", sa.String()),
        sa.column("version", sa.Integer()),
        sa.column("created_at", sa.DateTime(timezone=True)),
        sa.column("updated_at", sa.DateTime(timezone=True)),
    )
    op.bulk_insert(
        campaign,
        [
            {
                "code": "founder_v1",
                "state": "scheduled",
                "catalog_version": "v1",
                "version": 1,
                "created_at": now,
                "updated_at": now,
            }
        ],
    )


def downgrade() -> None:
    op.drop_index("ix_pricing_audit_event_type", table_name="pricing_audit_events")
    op.drop_index("ix_pricing_audit_created_at", table_name="pricing_audit_events")
    op.drop_table("pricing_audit_events")
    op.drop_table("founding_members")
    op.drop_index(
        "ix_checkout_reservation_expires_at",
        table_name="checkout_reservations",
    )
    op.drop_index(
        "ix_checkout_reservation_offer_status",
        table_name="checkout_reservations",
    )
    op.drop_index(
        "ix_checkout_reservation_user_status",
        table_name="checkout_reservations",
    )
    op.drop_table("checkout_reservations")
    op.drop_table("pricing_campaigns")
