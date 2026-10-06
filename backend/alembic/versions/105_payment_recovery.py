"""Minimal failure evidence and immutable bounded grace projection.
Revision ID: 105
Revises: 104
"""
import sqlalchemy as sa
from alembic import op
revision = "105"
down_revision = "104"
branch_labels = None
depends_on = None

def upgrade():
    op.add_column("subscriptions", sa.Column("recovery_due_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("subscriptions", sa.Column("grace_until", sa.DateTime(timezone=True), nullable=True))
    op.create_table("payment_recoveries",
        sa.Column('id', sa.UUID(), nullable=False, primary_key=True),
        sa.Column('user_id', sa.UUID(), nullable=False, primary_key=False),
        sa.Column('mandate_id', sa.UUID(), nullable=False, primary_key=False),
        sa.Column('source_event_id', sa.UUID(), nullable=False, primary_key=False),
        sa.Column('mode', sa.String(4), nullable=False, primary_key=False),
        sa.Column('account_id', sa.String(68), nullable=False, primary_key=False),
        sa.Column('invoice_id', sa.String(104), nullable=False, primary_key=False),
        sa.Column('provider_state', sa.String(16), nullable=False, primary_key=False),
        sa.Column('period_start', sa.DateTime(timezone=True), nullable=False, primary_key=False),
        sa.Column('period_end', sa.DateTime(timezone=True), nullable=False, primary_key=False),
        sa.Column('paid_through', sa.DateTime(timezone=True), nullable=False, primary_key=False),
        sa.Column('grace_until', sa.DateTime(timezone=True), nullable=False, primary_key=False),
        sa.Column('observed_at', sa.DateTime(timezone=True), nullable=False, primary_key=False),
        sa.Column('resolved_at', sa.DateTime(timezone=True), nullable=True, primary_key=False),
        sa.CheckConstraint("mode = 'test'", name='ck_recovery_mode'),
        sa.CheckConstraint('period_end > period_start AND paid_through <= period_start AND grace_until >= paid_through', name='ck_recovery_period'),
        sa.CheckConstraint("provider_state IN ('pending','halted')", name='ck_recovery_state'),
        sa.UniqueConstraint('mode', 'account_id', 'invoice_id', name='uq_recovery_invoice'),
        sa.UniqueConstraint('mandate_id', 'period_start', name='uq_recovery_period'),
    )
    op.create_index("ix_payment_recoveries_user_id", "payment_recoveries", ["user_id"])

def downgrade():
    bind = op.get_bind()
    if bind.scalar(sa.text("SELECT count(*) FROM payment_recoveries")) or bind.scalar(sa.text("SELECT count(*) FROM subscriptions WHERE recovery_due_at IS NOT NULL OR grace_until IS NOT NULL")):
        raise RuntimeError("Cannot discard payment recovery evidence")
    op.drop_table("payment_recoveries")
    op.drop_column("subscriptions", "grace_until")
    op.drop_column("subscriptions", "recovery_due_at")
