"""Preserve checkout evidence and add durable provider order claims.
Revision ID: 101
Revises: 100
"""
import sqlalchemy as sa
from alembic import op

revision = "101"
down_revision = "100"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("checkout_reservations", sa.Column("provider_order_state", sa.String(16), nullable=False, server_default="unstarted"))
    op.add_column("checkout_reservations", sa.Column("provider_key_id", sa.String(100)))
    op.add_column("checkout_reservations", sa.Column("provider_receipt", sa.String(40)))
    op.add_column("checkout_reservations", sa.Column("provider_started_at", sa.DateTime(timezone=True)))
    # Legacy unbound quotes might have crashed after creating a remote order.
    # No inferred key or remote absence; reconstruct only the old receipt.
    connection = op.get_bind()
    rows = connection.execute(sa.text("SELECT id, provider_order_id, status, reserved_at FROM checkout_reservations")).mappings()
    for row in rows:
        raw_id = str(row["id"]).replace("-", "")
        state = "ready" if row["provider_order_id"] else ("uncertain" if row["status"] == "reserved" else "unstarted")
        connection.execute(sa.text("UPDATE checkout_reservations SET provider_order_state=:state, provider_receipt=:receipt, provider_started_at=CASE WHEN :state='unstarted' THEN NULL ELSE reserved_at END WHERE id=:id"), {"state": state, "receipt": "fp-"+raw_id[:20], "id": row["id"]})


def downgrade():
    if op.get_bind().scalar(sa.text("SELECT count(*) FROM checkout_reservations WHERE provider_order_state <> 'unstarted'")):
        raise RuntimeError("Cannot discard provider order claim/reconciliation evidence")
    for column in ("provider_started_at", "provider_receipt", "provider_key_id", "provider_order_state"):
        op.drop_column("checkout_reservations", column)
