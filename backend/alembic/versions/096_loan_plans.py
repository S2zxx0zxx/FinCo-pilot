"""Workspace-scoped manual fixed-rate loan plans.

Revision ID: 096
Revises: 095
"""
from alembic import op
import sqlalchemy as sa

revision = "096"
down_revision = "095"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "loans",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("workspace_id", sa.Uuid(), sa.ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("principal", sa.Numeric(15, 2), nullable=False),
        sa.Column("annual_rate", sa.Numeric(7, 4), nullable=False),
        sa.Column("term_months", sa.Integer(), nullable=False),
        sa.Column("first_due_date", sa.Date(), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False),
        sa.Column("paid_installments", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("archived", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("principal >= 1 AND principal <= 999999999999", name="ck_loans_principal"),
        sa.CheckConstraint("annual_rate >= 0 AND annual_rate <= 60", name="ck_loans_rate"),
        sa.CheckConstraint("term_months >= 1 AND term_months <= 600", name="ck_loans_term"),
        sa.CheckConstraint("paid_installments >= 0 AND paid_installments <= term_months", name="ck_loans_paid"),
        sa.CheckConstraint("version >= 1", name="ck_loans_version"),
    )
    op.create_index("ix_loans_workspace_id", "loans", ["workspace_id"])


def downgrade() -> None:
    op.drop_table("loans")
