"""Add durable shared workspace deletion workflow; preserve all existing rows.
Revision ID: 100
Revises: 099
"""

import sqlalchemy as sa
from alembic import op

revision = "100"
down_revision = "099"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "workspace_deletions",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("workspace_id", sa.Uuid(), nullable=False),
        sa.Column(
            "requester_id",
            sa.Uuid(),
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("active_workspace_id", sa.Uuid(), unique=True),
        sa.Column("tracking_digest", sa.String(64), nullable=False),
        sa.Column("state", sa.String(32), nullable=False),
        sa.Column("blockers", sa.JSON(), nullable=False),
        sa.Column("manifest", sa.JSON(), nullable=False),
        sa.Column("review", sa.JSON(), nullable=False),
        sa.Column("receipts", sa.JSON(), nullable=False),
        sa.Column("lease_token", sa.String(64)),
        sa.Column("lease_until", sa.DateTime(timezone=True)),
        sa.Column("error_code", sa.String(64)),
        sa.Column("requested_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("primary_deleted_at", sa.DateTime(timezone=True)),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
    )
    op.create_index("ix_workspace_deletions_workspace_id", "workspace_deletions", ["workspace_id"])
    op.create_index("ix_workspace_deletions_requester_id", "workspace_deletions", ["requester_id"])
    op.create_table(
        "workspace_deletion_holds",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("workspace_id", sa.Uuid(), nullable=False),
        sa.Column("evidence_sha256", sa.String(64), nullable=False),
        sa.Column("reason", sa.String(40), nullable=False),
        sa.Column("verified_by", sa.String(36), nullable=False),
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("released_at", sa.DateTime(timezone=True)),
        sa.Column("released_by", sa.String(36)),
        sa.Column("release_evidence_sha256", sa.Text()),
    )
    op.create_index(
        "ix_workspace_deletion_holds_workspace_id", "workspace_deletion_holds", ["workspace_id"]
    )

    op.create_table(
        "workspace_deletion_events",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "deletion_id",
            sa.Uuid(),
            sa.ForeignKey("workspace_deletions.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("event_type", sa.String(40), nullable=False),
        sa.Column("actor_id", sa.String(36)),
        sa.Column("details", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "ix_workspace_deletion_events_deletion_id", "workspace_deletion_events", ["deletion_id"]
    )
    if op.get_bind().dialect.name == "postgresql":
        op.execute("""CREATE FUNCTION finco_fence_deleted_workspace() RETURNS trigger LANGUAGE plpgsql AS $$
        DECLARE subject uuid; BEGIN
          subject := (to_jsonb(NEW)->>TG_ARGV[0])::uuid;
          IF subject IS NOT NULL AND EXISTS (SELECT 1 FROM workspace_deletions WHERE workspace_id=subject AND state IN ('executing','external_retry','primary_workspace_deleted','backup_expiry_pending','complete')) THEN
            RAISE EXCEPTION 'Workspace deletion prevents late writes or resurrection' USING ERRCODE='23514';
          END IF;
          RETURN NEW;
        END $$;""")
        op.execute(
            """CREATE TRIGGER finco_workspace_tombstone BEFORE INSERT OR UPDATE ON workspaces FOR EACH ROW EXECUTE FUNCTION finco_fence_deleted_workspace('id');"""
        )
        op.execute(
            """CREATE TRIGGER finco_workspace_requester BEFORE INSERT OR UPDATE ON workspace_deletions FOR EACH ROW EXECUTE FUNCTION finco_fence_deleted_actor('requester_id');"""
        )
        op.execute("""DO $$ DECLARE item record; BEGIN
          FOR item IN SELECT c.conrelid::regclass AS relation, a.attname AS field, c.oid AS key_id
          FROM pg_constraint c JOIN pg_attribute a ON a.attrelid=c.conrelid AND a.attnum=c.conkey[1]
          WHERE c.contype='f' AND c.confrelid='workspaces'::regclass
          LOOP EXECUTE format('CREATE TRIGGER %I BEFORE INSERT OR UPDATE ON %s FOR EACH ROW EXECUTE FUNCTION finco_fence_deleted_workspace(%L)', 'finco_workspace_fence_'||item.key_id,item.relation,item.field); END LOOP;
        END $$;""")


def downgrade():
    for table in ("workspace_deletions", "workspace_deletion_holds", "workspace_deletion_events"):
        if op.get_bind().scalar(sa.text(f"SELECT count(*) FROM {table}")):
            raise RuntimeError("Refusing to destroy workspace deletion or hold evidence")
    if op.get_bind().dialect.name == "postgresql":
        op.execute("""DO $$ DECLARE item record; BEGIN
          FOR item IN SELECT tgname, tgrelid::regclass AS relation FROM pg_trigger JOIN pg_class ON pg_class.oid=tgrelid JOIN pg_namespace ON pg_namespace.oid=pg_class.relnamespace WHERE tgname LIKE 'finco_workspace_fence_%' AND nspname=current_schema()
          LOOP EXECUTE format('DROP TRIGGER %I ON %s',item.tgname,item.relation); END LOOP;
        END $$;""")
        op.execute("DROP TRIGGER finco_workspace_requester ON workspace_deletions")
        op.execute("DROP TRIGGER finco_workspace_tombstone ON workspaces")
        op.execute("DROP FUNCTION finco_fence_deleted_workspace()")
    op.drop_table("workspace_deletion_events")
    op.drop_table("workspace_deletion_holds")
    op.drop_table("workspace_deletions")
