"""Durable minimal signed-payment receipts.
Revision ID: 102
Revises: 101
"""
import sqlalchemy as sa
from alembic import op

revision = "102"
down_revision = "101"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table("payment_webhook_events",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column("provider", sa.String(16), nullable=False),
        sa.Column("mode", sa.String(4), nullable=False),
        sa.Column("account_id", sa.String(68), nullable=False),
        sa.Column("body_sha256", sa.String(64), nullable=False),
        sa.Column("event_type", sa.String(128), nullable=False),
        sa.Column("delivery_hint", sa.String(128)),
        sa.Column("state", sa.String(16), nullable=False),
        sa.Column("snapshot_ciphertext", sa.Text(), nullable=False),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("provider", "mode", "account_id", "body_sha256", name="uq_payment_webhook_body"),
        sa.CheckConstraint("provider = 'razorpay'", name="ck_payment_webhook_provider"),
        sa.CheckConstraint("mode IN ('test','live')", name="ck_payment_webhook_mode"),
        sa.CheckConstraint("state IN ('pending','quarantined','processed')", name="ck_payment_webhook_state"),
        sa.CheckConstraint("length(body_sha256) = 64", name="ck_payment_webhook_hash"),
        sa.CheckConstraint("snapshot_ciphertext LIKE 'payment-inbox:v1:%' AND length(snapshot_ciphertext) <= 65536", name="ck_payment_webhook_ciphertext"),
    )
    op.create_index("ix_payment_webhook_events_state", "payment_webhook_events", ["state"])


def downgrade():
    if op.get_bind().scalar(sa.text("SELECT count(*) FROM payment_webhook_events")):
        raise RuntimeError("Cannot discard acknowledged payment webhook evidence")
    op.drop_table("payment_webhook_events")
