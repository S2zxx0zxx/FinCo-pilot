"""Retained refunds and paid-term revocation projection.
Revision ID: 107
Revises: 106
"""
import sqlalchemy as sa
from alembic import op
revision = "107"
down_revision = "106"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("subscriptions", sa.Column("paid_term_refunded", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.create_table("payment_refunds",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("source_id", sa.UUID(), nullable=False),
        sa.Column("source_kind", sa.String(16), nullable=False),
        sa.Column("mode", sa.String(4), nullable=False),
        sa.Column("account_id", sa.String(68), nullable=False),
        sa.Column("provider_key_id", sa.String(100), nullable=False),
        sa.Column("payment_id", sa.String(104), nullable=False),
        sa.Column("amount_minor", sa.Integer(), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False),
        sa.Column("operator_id", sa.UUID(), nullable=False),
        sa.Column("evidence_sha256", sa.String(64), nullable=False),
        sa.Column("state", sa.String(16), nullable=False),
        sa.Column("requested_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("refund_id", sa.String(104)),
        sa.UniqueConstraint("mode", "account_id", "payment_id", name="uq_refund_dispatch_payment"),
        sa.CheckConstraint("mode = 'test' AND currency = 'INR' AND amount_minor >= 100", name="ck_refund_dispatch_scope"),
        sa.CheckConstraint("state IN ('sending','uncertain','pending','processed','failed','external')", name="ck_refund_dispatch_state"),
        sa.CheckConstraint("source_kind IN ('activation','renewal')", name="ck_refund_dispatch_source"))
    op.create_index("ix_payment_refunds_user_id", "payment_refunds", ["user_id"])
    op.create_table("refund_observations",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("mode", sa.String(4), nullable=False),
        sa.Column("account_id", sa.String(68), nullable=False),
        sa.Column("payment_id", sa.String(104), nullable=False),
        sa.Column("refund_id", sa.String(104), nullable=False),
        sa.Column("amount_minor", sa.Integer(), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False),
        sa.Column("state", sa.String(16), nullable=False),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("mode", "account_id", "refund_id", name="uq_refund_observation_identity"),
        sa.CheckConstraint("mode = 'test' AND currency = 'INR' AND amount_minor > 0", name="ck_refund_observation_scope"),
        sa.CheckConstraint("state IN ('pending','processed','failed')", name="ck_refund_observation_state"))
    op.create_index("ix_refund_observations_user_id", "refund_observations", ["user_id"])


def downgrade():
    bind = op.get_bind()
    if any(bind.scalar(sa.text("SELECT count(*) FROM " + name)) for name in ("payment_refunds", "refund_observations")):
        raise RuntimeError("Cannot discard refund evidence")
    if bind.scalar(sa.text("SELECT count(*) FROM subscriptions WHERE paid_term_refunded")):
        raise RuntimeError("Cannot discard refunded entitlement projection")
    op.drop_table("refund_observations")
    op.drop_table("payment_refunds")
    op.drop_column("subscriptions", "paid_term_refunded")
