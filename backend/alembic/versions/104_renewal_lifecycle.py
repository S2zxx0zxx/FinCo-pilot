"""Durable finite renewal mandate and paid cycle evidence.
Revision ID: 104
Revises: 103
"""
import sqlalchemy as sa
from alembic import op

revision = "104"
down_revision = "103"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('renewal_mandates',
        sa.Column('id', sa.UUID(), nullable=False, primary_key=True),
        sa.Column('user_id', sa.UUID(), nullable=False, primary_key=False),
        sa.Column('active_user_id', sa.UUID(), nullable=True, primary_key=False),
        sa.Column('activation_id', sa.UUID(), nullable=False, primary_key=False),
        sa.Column('subscription_id', sa.UUID(), nullable=False, primary_key=False),
        sa.Column('mode', sa.String(4), nullable=False, primary_key=False),
        sa.Column('account_id', sa.String(68), nullable=False, primary_key=False),
        sa.Column('provider_key_id', sa.String(100), nullable=False, primary_key=False),
        sa.Column('provider_plan_id', sa.String(104), nullable=False, primary_key=False),
        sa.Column('provider_subscription_id', sa.String(104), nullable=True, primary_key=False),
        sa.Column('plan', sa.String(16), nullable=False, primary_key=False),
        sa.Column('billing_interval', sa.String(16), nullable=False, primary_key=False),
        sa.Column('amount_minor', sa.Integer(), nullable=False, primary_key=False),
        sa.Column('currency', sa.String(3), nullable=False, primary_key=False),
        sa.Column('total_count', sa.Integer(), nullable=False, primary_key=False),
        sa.Column('starts_at', sa.DateTime(timezone=True), nullable=False, primary_key=False),
        sa.Column('requested_at', sa.DateTime(timezone=True), nullable=False, primary_key=False),
        sa.Column('state', sa.String(16), nullable=False, primary_key=False),
        sa.CheckConstraint('total_count BETWEEN 1 AND 120', name='ck_renewal_count'),
        sa.CheckConstraint("plan IN ('pro','max') AND billing_interval IN ('monthly','annual')", name='ck_renewal_plan'),
        sa.CheckConstraint("mode = 'test' AND currency = 'INR' AND amount_minor > 0", name='ck_renewal_scope'),
        sa.CheckConstraint("state IN ('unstarted','creating','uncertain','ready','completed','expired')", name='ck_renewal_state'),
        sa.UniqueConstraint('active_user_id', name='uq_renewal_active_user'),
        sa.UniqueConstraint('mode', 'account_id', 'provider_subscription_id', name='uq_renewal_provider_subscription'),
    )
    op.create_index("ix_renewal_mandates_user_id", 'renewal_mandates', ["user_id"])
    op.create_table('renewal_cycles',
        sa.Column('id', sa.UUID(), nullable=False, primary_key=True),
        sa.Column('user_id', sa.UUID(), nullable=False, primary_key=False),
        sa.Column('mandate_id', sa.UUID(), nullable=False, primary_key=False),
        sa.Column('source_event_id', sa.UUID(), nullable=False, primary_key=False),
        sa.Column('mode', sa.String(4), nullable=False, primary_key=False),
        sa.Column('account_id', sa.String(68), nullable=False, primary_key=False),
        sa.Column('provider_subscription_id', sa.String(104), nullable=False, primary_key=False),
        sa.Column('invoice_id', sa.String(104), nullable=False, primary_key=False),
        sa.Column('payment_id', sa.String(104), nullable=False, primary_key=False),
        sa.Column('amount_minor', sa.Integer(), nullable=False, primary_key=False),
        sa.Column('currency', sa.String(3), nullable=False, primary_key=False),
        sa.Column('period_start', sa.DateTime(timezone=True), nullable=False, primary_key=False),
        sa.Column('period_end', sa.DateTime(timezone=True), nullable=False, primary_key=False),
        sa.Column('applied_at', sa.DateTime(timezone=True), nullable=False, primary_key=False),
        sa.CheckConstraint('period_end > period_start', name='ck_renewal_cycle_period'),
        sa.CheckConstraint("mode = 'test' AND currency = 'INR' AND amount_minor > 0", name='ck_renewal_cycle_scope'),
        sa.UniqueConstraint('mandate_id', 'period_start', name='uq_renewal_cycle'),
        sa.UniqueConstraint('mode', 'account_id', 'invoice_id', name='uq_renewal_invoice'),
        sa.UniqueConstraint('mode', 'account_id', 'payment_id', name='uq_renewal_payment'),
    )
    op.create_index("ix_renewal_cycles_user_id", 'renewal_cycles', ["user_id"])


def downgrade():
    bind = op.get_bind()
    if any(bind.scalar(sa.text("SELECT count(*) FROM " + table)) for table in ("renewal_cycles", "renewal_mandates")):
        raise RuntimeError("Cannot discard renewal mandate/cycle evidence")
    op.drop_table("renewal_cycles")
    op.drop_table("renewal_mandates")
