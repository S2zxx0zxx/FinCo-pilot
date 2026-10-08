"""Require explicit classification of ambiguous SimpleFIN checking defaults.

Revision ID: 108
Revises: 107
"""
from alembic import op
import sqlalchemy as sa

revision = "108"
down_revision = "107"
branch_labels = None
depends_on = None


def upgrade():
    # Old checking rows carry no provenance: even genuine checking accounts
    # must be reconfirmed. Other explicit user choices and all financial data
    # remain untouched. No guessing from names, signs or available credit.
    op.execute(sa.text("""
        UPDATE accounts SET type = 'unknown'
        WHERE type = 'checking' AND connection_id IN
            (SELECT id FROM bank_connections WHERE provider = 'simplefin')
    """))


def downgrade():
    # Never invent a checking classification when rolling back the application.
    if op.get_bind().scalar(sa.text("""
        SELECT count(*) FROM accounts WHERE type IN ('unknown', 'loan')
        AND connection_id IN
            (SELECT id FROM bank_connections WHERE provider = 'simplefin')
    """)):
        raise RuntimeError("Cannot discard unresolved SimpleFIN classification")
