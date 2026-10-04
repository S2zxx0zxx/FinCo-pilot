"""Add durable personal deletion workflow; preserve all existing rows.
Revision ID: 099
Revises: 098
"""
import sqlalchemy as sa
from alembic import op
revision = "099"
down_revision = "098"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table("account_deletions",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("active_user_id", sa.Uuid(), unique=True),
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
        sa.Column("completed_at", sa.DateTime(timezone=True)))
    op.create_index("ix_account_deletions_user_id", "account_deletions", ["user_id"])
    op.create_table("account_deletion_holds",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("evidence_sha256", sa.String(64), nullable=False),
        sa.Column("reason", sa.String(40), nullable=False),
        sa.Column("verified_by", sa.String(36), nullable=False),
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("released_at", sa.DateTime(timezone=True)),
        sa.Column("released_by", sa.String(36)),
        sa.Column("release_evidence_sha256", sa.Text()))
    op.create_index("ix_account_deletion_holds_user_id", "account_deletion_holds", ["user_id"])

    op.create_table("account_deletion_events",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("deletion_id", sa.Uuid(), sa.ForeignKey("account_deletions.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("event_type", sa.String(40), nullable=False),
        sa.Column("actor_id", sa.String(36)),
        sa.Column("details", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False))
    op.create_index("ix_account_deletion_events_deletion_id", "account_deletion_events", ["deletion_id"])
    if op.get_bind().dialect.name == "postgresql":
        op.execute("""
        CREATE FUNCTION finco_fence_deleted_actor() RETURNS trigger LANGUAGE plpgsql AS $$
        DECLARE subject uuid;
        BEGIN
          IF TG_OP = 'UPDATE' AND (to_jsonb(NEW)->TG_ARGV[0]) IS NOT DISTINCT FROM (to_jsonb(OLD)->TG_ARGV[0]) THEN RETURN NEW; END IF;
          subject := (to_jsonb(NEW)->>TG_ARGV[0])::uuid;
          IF subject IS NOT NULL AND EXISTS (SELECT 1 FROM account_deletions WHERE user_id=subject AND state IN ('executing','external_retry','primary_data_deleted','backup_expiry_pending','complete')) THEN
            RAISE EXCEPTION 'Deleted actor cannot acquire new data or access' USING ERRCODE='23514';
          END IF;
          RETURN NEW;
        END $$;
        """)
        op.execute("""
        CREATE FUNCTION finco_protect_deletion_tombstone() RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
          IF OLD.hashed_password LIKE '!deleted:%' AND EXISTS (SELECT 1 FROM account_deletions WHERE user_id=OLD.id AND state IN ('executing','external_retry','primary_data_deleted','backup_expiry_pending','complete')) THEN
            RAISE EXCEPTION 'Deletion tombstones are immutable' USING ERRCODE='23514';
          END IF;
          RETURN NEW;
        END $$;
        """)
        op.execute("""
        CREATE TRIGGER finco_protect_deletion_tombstone BEFORE UPDATE ON users FOR EACH ROW EXECUTE FUNCTION finco_protect_deletion_tombstone();
        """)
        op.execute("""
        DO $$ DECLARE item record; BEGIN
          FOR item IN
            SELECT c.conrelid::regclass AS relation, a.attname AS field, c.oid AS key_id
            FROM pg_constraint c JOIN pg_attribute a ON a.attrelid=c.conrelid AND a.attnum=c.conkey[1]
            WHERE c.contype='f' AND c.confrelid='users'::regclass
              AND c.conrelid NOT IN ('account_deletions'::regclass,'account_deletion_holds'::regclass)
          LOOP
            EXECUTE format('CREATE TRIGGER %I BEFORE INSERT OR UPDATE ON %s FOR EACH ROW EXECUTE FUNCTION finco_fence_deleted_actor(%L)', 'finco_deleted_actor_'||item.key_id, item.relation, item.field);
          END LOOP;
        END $$;
        """)


def downgrade():
    for table in ("account_deletions", "account_deletion_holds", "account_deletion_events"):
        if op.get_bind().scalar(sa.text(f"SELECT count(*) FROM {table}")):
            raise RuntimeError("Refusing to destroy deletion receipts or hold evidence")
    if op.get_bind().dialect.name == "postgresql":
        op.execute("""
        DO $$ DECLARE item record; BEGIN
          FOR item IN SELECT tgname, tgrelid::regclass AS relation FROM pg_trigger JOIN pg_class ON pg_class.oid=tgrelid JOIN pg_namespace ON pg_namespace.oid=pg_class.relnamespace WHERE tgname LIKE 'finco_deleted_actor_%' AND nspname=current_schema()
          LOOP EXECUTE format('DROP TRIGGER %I ON %s', item.tgname, item.relation); END LOOP;
        END $$;
        """)
        op.execute("""
        DROP TRIGGER finco_protect_deletion_tombstone ON users;
        """)
        op.execute("""
        DROP FUNCTION finco_protect_deletion_tombstone();
        """)
        op.execute("""
        DROP FUNCTION finco_fence_deleted_actor();
        """)
    op.drop_table("account_deletion_events")
    op.drop_table("account_deletion_holds")
    op.drop_table("account_deletions")
