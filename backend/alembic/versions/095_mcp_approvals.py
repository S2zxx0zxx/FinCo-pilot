"""Human approval for external MCP writes.

Revision ID: 095
Revises: 094
"""
from alembic import op
import sqlalchemy as sa

revision = '095'
down_revision = '094'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table('mcp_approvals',
        sa.Column('id', sa.Uuid(), primary_key=True),
        sa.Column('token_id', sa.Uuid(), sa.ForeignKey('external_mcp_tokens.id', ondelete='CASCADE'), nullable=False),
        sa.Column('user_id', sa.Uuid(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('workspace_id', sa.Uuid(), sa.ForeignKey('workspaces.id', ondelete='CASCADE'), nullable=False),
        sa.Column('tool_name', sa.String(120), nullable=False),
        sa.Column('arguments', sa.JSON(), nullable=False),
        sa.Column('status', sa.String(20), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
    )
    for name in ('token_id', 'user_id', 'workspace_id'):
        op.create_index(f'ix_mcp_approvals_{name}', 'mcp_approvals', [name])


def downgrade() -> None:
    op.drop_table('mcp_approvals')
