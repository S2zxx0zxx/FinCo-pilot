"""make INR the default currency for new FinCo-Pilot records

This changes database-level defaults only. Existing rows are deliberately not
backfilled: a workspace/account/group that explicitly uses USD (or any other
currency) keeps that choice. New records created without an explicit currency
inherit INR, matching the application and onboarding defaults.
"""
from alembic import op

revision = "090"
down_revision = "089"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column("budgets", "currency", server_default="INR")
    op.alter_column("goals", "currency", server_default="INR")
    op.alter_column("groups", "default_currency", server_default="INR")
    op.alter_column("workspaces", "default_currency", server_default="INR")
    op.alter_column("invoices", "currency", server_default="INR")


def downgrade() -> None:
    op.alter_column("budgets", "currency", server_default="USD")
    op.alter_column("goals", "currency", server_default="USD")
    op.alter_column("groups", "default_currency", server_default="USD")
    op.alter_column("workspaces", "default_currency", server_default="USD")
    op.alter_column("invoices", "currency", server_default="USD")
