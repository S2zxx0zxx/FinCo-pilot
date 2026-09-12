"""Add billing usage counters and backfill Free subscription rows.

Revision ID: 092
Revises: 091
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "092"
down_revision = "091"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "billing_usage_counters",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("metric", sa.String(length=64), nullable=False),
        sa.Column("period_start", sa.Date(), nullable=False),
        sa.Column("used", sa.Integer(), server_default="0", nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "user_id",
            "metric",
            "period_start",
            name="uq_billing_usage_user_metric_period",
        ),
    )
    op.create_index(
        "ix_billing_usage_counters_user_id",
        "billing_usage_counters",
        ["user_id"],
        unique=False,
    )
    op.create_index(
        "ix_billing_usage_counters_metric",
        "billing_usage_counters",
        ["metric"],
        unique=False,
    )
    op.create_index(
        "ix_billing_usage_counters_period_start",
        "billing_usage_counters",
        ["period_start"],
        unique=False,
    )

    # Every billing owner needs a stable row that can be locked while a hard
    # quota is checked. Existing users therefore receive an explicit Free row;
    # the application also creates one during new-user bootstrap.
    op.execute(
        """
        INSERT INTO subscriptions (
            id, user_id, plan, status, billing_interval,
            cancel_at_period_end, created_at, updated_at
        )
        SELECT
            gen_random_uuid(), u.id, 'free', 'free', 'none',
            false, now(), now()
        FROM users AS u
        WHERE NOT EXISTS (
            SELECT 1 FROM subscriptions AS s WHERE s.user_id = u.id
        )
        """
    )


def downgrade() -> None:
    op.drop_index("ix_billing_usage_counters_period_start", table_name="billing_usage_counters")
    op.drop_index("ix_billing_usage_counters_metric", table_name="billing_usage_counters")
    op.drop_index("ix_billing_usage_counters_user_id", table_name="billing_usage_counters")
    op.drop_table("billing_usage_counters")
