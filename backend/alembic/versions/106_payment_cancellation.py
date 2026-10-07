"""Retained cancellation outcome and at-most-once dispatch.
Revision ID: 106
Revises: 105
"""
import sqlalchemy as sa
from alembic import op
revision = "106"
down_revision = "105"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table("payment_cancellations",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("mandate_id", sa.UUID(), nullable=False),
        sa.Column("mode", sa.String(4), nullable=False),
        sa.Column("account_id", sa.String(68), nullable=False),
        sa.Column("provider_key_id", sa.String(100), nullable=False),
        sa.Column("provider_subscription_id", sa.String(104), nullable=False),
        sa.Column("state", sa.String(16), nullable=False),
        sa.Column("requested_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("confirmed_at", sa.DateTime(timezone=True)),
        sa.UniqueConstraint("mandate_id", name="uq_cancellation_mandate"),
        sa.CheckConstraint("state IN ('sending','uncertain','confirmed')", name="ck_cancellation_state"),
        sa.CheckConstraint("mode = 'test'", name="ck_cancellation_mode"),
    )
    op.create_index("ix_payment_cancellations_user_id", "payment_cancellations", ["user_id"])


def downgrade():
    if op.get_bind().scalar(sa.text("SELECT count(*) FROM payment_cancellations")):
        raise RuntimeError("Cannot discard cancellation evidence")
    op.drop_table("payment_cancellations")
