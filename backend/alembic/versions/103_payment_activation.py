"""Idempotent paid activation and recoverable inbox processing.
Revision ID: 103
Revises: 102
"""
import sqlalchemy as sa
from alembic import op

revision = "103"
down_revision = "102"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table("payment_activations",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column("provider", sa.String(16), nullable=False),
        sa.Column("mode", sa.String(4), nullable=False),
        sa.Column("account_id", sa.String(68), nullable=False),
        sa.Column("provider_key_id", sa.String(100), nullable=False),
        sa.Column("payment_id", sa.String(104), nullable=False),
        sa.Column("order_id", sa.String(106), nullable=False),
        sa.Column("reservation_id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("source_event_id", sa.UUID(), nullable=False),
        sa.Column("plan", sa.String(16), nullable=False),
        sa.Column("billing_interval", sa.String(16), nullable=False),
        sa.Column("amount_minor", sa.Integer(), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False),
        sa.Column("period_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("period_end", sa.DateTime(timezone=True), nullable=False),
        sa.Column("applied_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("provider", "mode", "account_id", "payment_id", name="uq_payment_activation_identity"),
        sa.UniqueConstraint("reservation_id", name="uq_payment_activation_reservation"),
        sa.CheckConstraint("provider = 'razorpay'", name="ck_payment_activation_provider"),
        sa.CheckConstraint("mode IN ('test','live')", name="ck_payment_activation_mode"),
        sa.CheckConstraint("plan IN ('pro','max')", name="ck_payment_activation_plan"),
        sa.CheckConstraint("billing_interval IN ('monthly','annual')", name="ck_payment_activation_interval"),
        sa.CheckConstraint("amount_minor > 0 AND currency = 'INR'", name="ck_payment_activation_amount"),
        sa.CheckConstraint("period_end > period_start", name="ck_payment_activation_period"),
    )
    op.create_index("ix_payment_activations_user_id", "payment_activations", ["user_id"])
    op.add_column("payment_webhook_events", sa.Column("processing_attempts", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("payment_webhook_events", sa.Column("next_attempt_at", sa.DateTime(timezone=True)))
    op.add_column("payment_webhook_events", sa.Column("processing_error", sa.String(40)))
    op.add_column("payment_webhook_events", sa.Column("processed_at", sa.DateTime(timezone=True)))
    op.create_index("ix_payment_webhook_due", "payment_webhook_events", ["state", "next_attempt_at", "received_at"])
    # SQLite requires table recreation to add a check to an existing table.
    with op.batch_alter_table("payment_webhook_events") as batch:
        batch.create_check_constraint("ck_payment_webhook_attempts", "processing_attempts >= 0")


def downgrade():
    bind = op.get_bind()
    if (bind.scalar(sa.text("SELECT count(*) FROM payment_activations"))
            or bind.scalar(sa.text("SELECT count(*) FROM payment_webhook_events WHERE processing_attempts > 0"))):
        raise RuntimeError("Cannot discard payment activation/processing evidence")
    with op.batch_alter_table("payment_webhook_events") as batch:
        batch.drop_constraint("ck_payment_webhook_attempts", type_="check")
    op.drop_index("ix_payment_webhook_due", table_name="payment_webhook_events")
    for name in ("processed_at", "processing_error", "next_attempt_at", "processing_attempts"):
        op.drop_column("payment_webhook_events", name)
    op.drop_table("payment_activations")
