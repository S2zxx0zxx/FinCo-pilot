"""Add external authentication identity mapping without touching users or finances.

Revision ID: 109
Revises: 108
"""
import sqlalchemy as sa
from alembic import op

revision = "109"
down_revision = "108"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "external_auth_identities",
        sa.Column("id", sa.Uuid(), primary_key=True, nullable=False),
        sa.Column("provider", sa.String(32), nullable=False),
        sa.Column("issuer", sa.String(255), nullable=False),
        sa.Column("provider_subject", sa.String(255), nullable=False),
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("provider", "issuer", "provider_subject", name="uq_external_auth_identity"),
        sa.UniqueConstraint("provider", "issuer", "user_id", name="uq_external_auth_user"),
    )
    op.create_index("ix_external_auth_identities_user_id", "external_auth_identities", ["user_id"])


def downgrade():
    # This table may contain the only binding between a Clerk account and
    # existing financial records. Never silently discard it during rollback.
    count = op.get_bind().scalar(sa.text("SELECT count(*) FROM external_auth_identities"))
    if count:
        raise RuntimeError("Refusing to delete populated external identity mappings")
    op.drop_index("ix_external_auth_identities_user_id", table_name="external_auth_identities")
    op.drop_table("external_auth_identities")
