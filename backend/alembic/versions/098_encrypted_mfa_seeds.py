"""Widen authenticator storage without altering or deleting existing seeds.

Revision ID: 098
Revises: 097
"""
import sqlalchemy as sa
from alembic import op

revision = "098"
down_revision = "097"
branch_labels = None
depends_on = None


def upgrade() -> None:
    if op.get_bind().dialect.name == "postgresql":
        op.execute("SET LOCAL lock_timeout = '5s'")
    op.alter_column("users", "totp_secret", existing_type=sa.String(32), type_=sa.Text(), existing_nullable=True)


def downgrade() -> None:
    # Never truncate encrypted credentials to fit the former column. On a live
    # encrypted database, keep the widened schema and roll application forward.
    count = op.get_bind().scalar(sa.text("SELECT count(*) FROM users WHERE length(totp_secret) > 32"))
    if count:
        raise RuntimeError("Refusing to narrow authenticator storage: encrypted data must be preserved")
    op.alter_column("users", "totp_secret", existing_type=sa.Text(), type_=sa.String(32), existing_nullable=True)
