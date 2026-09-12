"""Add billing entitlement foundation.

Revision ID: 091
Revises: 090
"""

import uuid
from datetime import datetime, timezone

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "091"
down_revision = "090"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "subscriptions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("plan", sa.String(length=16), server_default="free", nullable=False),
        sa.Column("status", sa.String(length=20), server_default="free", nullable=False),
        sa.Column("billing_interval", sa.String(length=16), server_default="none", nullable=False),
        sa.Column("current_period_start", sa.DateTime(timezone=True), nullable=True),
        sa.Column("current_period_end", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancel_at_period_end", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("provider", sa.String(length=40), nullable=True),
        sa.Column("provider_customer_id", sa.String(length=255), nullable=True),
        sa.Column("provider_subscription_id", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", name="uq_subscriptions_user_id"),
    )
    op.create_index("ix_subscriptions_user_id", "subscriptions", ["user_id"], unique=False)

    # Every user — including legacy users and Free users — gets a billing row.
    # Besides making Free explicit, this row is the transaction-lock anchor for
    # race-safe current-resource quota checks.
    bind = op.get_bind()
    user_ids = list(bind.execute(sa.text("SELECT id FROM users")).scalars())
    if user_ids:
        now = datetime.now(timezone.utc)
        subscriptions = sa.table(
            "subscriptions",
            sa.column("id", postgresql.UUID(as_uuid=True)),
            sa.column("user_id", postgresql.UUID(as_uuid=True)),
            sa.column("plan", sa.String()),
            sa.column("status", sa.String()),
            sa.column("billing_interval", sa.String()),
            sa.column("cancel_at_period_end", sa.Boolean()),
            sa.column("created_at", sa.DateTime(timezone=True)),
            sa.column("updated_at", sa.DateTime(timezone=True)),
        )
        op.bulk_insert(
            subscriptions,
            [
                {
                    "id": uuid.uuid4(),
                    "user_id": user_id,
                    "plan": "free",
                    "status": "free",
                    "billing_interval": "none",
                    "cancel_at_period_end": False,
                    "created_at": now,
                    "updated_at": now,
                }
                for user_id in user_ids
            ],
        )

    op.add_column(
        "workspaces",
        sa.Column("billing_owner_user_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_workspaces_billing_owner_user_id_users",
        "workspaces",
        "users",
        ["billing_owner_user_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "ix_workspaces_billing_owner_user_id",
        "workspaces",
        ["billing_owner_user_id"],
        unique=False,
    )

    # Audit creator is the best deterministic billing owner for normal legacy
    # rows; externally managed historical rows use their manager only when the
    # creator is missing.
    op.execute(
        """
        UPDATE workspaces
        SET billing_owner_user_id = COALESCE(created_by_user_id, managed_by_user_id)
        WHERE billing_owner_user_id IS NULL
        """
    )

    # Malformed/very old rows may lack both audit fields. Resolve only a real
    # owner membership, deterministically, rather than assigning any member.
    op.execute(
        """
        UPDATE workspaces AS w
        SET billing_owner_user_id = (
            SELECT wm.user_id
            FROM workspace_members AS wm
            WHERE wm.workspace_id = w.id AND wm.role = 'owner'
            ORDER BY wm.joined_at ASC, wm.id ASC
            LIMIT 1
        )
        WHERE w.billing_owner_user_id IS NULL
        """
    )


def downgrade() -> None:
    op.drop_index("ix_workspaces_billing_owner_user_id", table_name="workspaces")
    op.drop_constraint(
        "fk_workspaces_billing_owner_user_id_users", "workspaces", type_="foreignkey"
    )
    op.drop_column("workspaces", "billing_owner_user_id")

    op.drop_index("ix_subscriptions_user_id", table_name="subscriptions")
    op.drop_table("subscriptions")
