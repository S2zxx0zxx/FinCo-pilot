"""Add bank sync freshness and job-state columns.

Revision ID: 086
Revises: 085
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "086"
down_revision: Union[str, None] = "085"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "bank_connections",
        sa.Column("last_sync_started_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "bank_connections",
        sa.Column("last_provider_refresh_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "bank_connections",
        sa.Column(
            "last_sync_status",
            sa.String(length=50),
            nullable=False,
            server_default="idle",
        ),
    )
    op.add_column(
        "bank_connections",
        sa.Column("last_sync_error", sa.String(length=1000), nullable=True),
    )
    op.create_index(
        "ix_bank_connections_sync_status",
        "bank_connections",
        ["last_sync_status"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_bank_connections_sync_status", table_name="bank_connections")
    op.drop_column("bank_connections", "last_sync_error")
    op.drop_column("bank_connections", "last_sync_status")
    op.drop_column("bank_connections", "last_provider_refresh_at")
    op.drop_column("bank_connections", "last_sync_started_at")
