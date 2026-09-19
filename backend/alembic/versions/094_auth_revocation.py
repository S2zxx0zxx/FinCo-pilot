"""Durable credential epoch for session revocation.

Revision ID: 094
Revises: 093
"""
from alembic import op
import sqlalchemy as sa

revision = "094"
down_revision = "093"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("recovery_code_hashes", sa.JSON(), nullable=True))
    op.add_column("users", sa.Column("auth_epoch", sa.String(36), nullable=False, server_default=""))

    op.create_table(
        "external_mcp_tokens",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("workspace_id", sa.Uuid(), sa.ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False),
        sa.Column("credential_stamp", sa.String(64), nullable=False),
        sa.Column("allow_writes", sa.Boolean(), nullable=False),
        sa.Column("revoked", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_external_mcp_tokens_user_id", "external_mcp_tokens", ["user_id"])
    op.create_index("ix_external_mcp_tokens_workspace_id", "external_mcp_tokens", ["workspace_id"])


def downgrade() -> None:
    op.drop_table("external_mcp_tokens")
    op.drop_column("users", "auth_epoch")
    op.drop_column("users", "recovery_code_hashes")
