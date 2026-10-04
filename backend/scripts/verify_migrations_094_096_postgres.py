"""Isolated, populated PostgreSQL proof for roadmap #20; never production acceptance."""
import asyncio
import importlib.util
import os
import uuid
from pathlib import Path

from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import create_async_engine


def apply_revision(connection, revision):
    paths = list((Path(__file__).resolve().parents[1] / "alembic" / "versions").glob(f"{revision}_*.py"))
    if len(paths) != 1:
        raise RuntimeError("Expected exactly one reviewed migration")
    spec = importlib.util.spec_from_file_location(f"revision_{revision}", paths[0])
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    with Operations.context(MigrationContext.configure(connection)):
        module.upgrade()


async def main():
    # Guard precedes runtime imports/connection creation. Never reuse a public schema.
    if os.environ.get("CI") != "true" or os.environ.get("FINCO_DISPOSABLE_DB_TEST") != "yes":
        raise SystemExit("Refusing proof outside explicitly disposable CI")
    from app.core.database import engine

    schema = "migration20_ci_" + uuid.uuid4().hex
    isolated = create_async_engine(engine.url, connect_args={"server_settings": {"search_path": schema}})
    owner, workspace, token = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
    try:
        async with engine.begin() as connection:
            await connection.execute(text(f'CREATE SCHEMA "{schema}"'))
        async with isolated.begin() as connection:
            # Minimal pre-094 dependency fixture: this is not a full production clone.
            await connection.execute(text("CREATE TABLE users (id uuid PRIMARY KEY, hashed_password text NOT NULL, totp_secret varchar(32))"))
            await connection.execute(text("CREATE TABLE workspaces (id uuid PRIMARY KEY, name text NOT NULL)"))
            await connection.execute(text("INSERT INTO users VALUES (:id, 'synthetic-hash', 'SYNTHETIC-SEED')"), {"id": owner})
            await connection.execute(text("INSERT INTO workspaces VALUES (:id, 'synthetic-workspace')"), {"id": workspace})
            assert await connection.scalar(text("SELECT current_schema()")) == schema
        # A migration failure must roll back prior DDL in the same transaction.
        try:
            async with isolated.begin() as connection:
                await connection.run_sync(lambda sync: apply_revision(sync, "094"))
                raise RuntimeError("synthetic failure after DDL")
        except RuntimeError as exc:
            if str(exc) != "synthetic failure after DDL":
                raise
        async with isolated.connect() as connection:
            assert await connection.scalar(text("SELECT to_regclass('external_mcp_tokens')")) is None
            assert await connection.scalar(text("SELECT count(*) FROM information_schema.columns WHERE table_schema=:schema AND table_name='users' AND column_name='auth_epoch'"), {"schema": schema}) == 0
        async with isolated.begin() as connection:
            await connection.execute(text("SET LOCAL lock_timeout = '5s'"))
            for revision in ("094", "095", "096"):
                await connection.run_sync(lambda sync, revision=revision: apply_revision(sync, revision))
            row = (await connection.execute(text("SELECT hashed_password,totp_secret,auth_epoch,recovery_code_hashes FROM users WHERE id=:id"), {"id": owner})).one()
            assert tuple(row) == ("synthetic-hash", "SYNTHETIC-SEED", "", None)
            assert await connection.scalar(text("SELECT name FROM workspaces WHERE id=:id"), {"id": workspace}) == "synthetic-workspace"
            await connection.execute(text("INSERT INTO external_mcp_tokens VALUES (:id,:user,:workspace,:stamp,false,false,now(),now()+interval '1 hour')"), {"id": token, "user": owner, "workspace": workspace, "stamp": "a" * 64})
            await connection.execute(text("INSERT INTO mcp_approvals VALUES (:id,:token,:user,:workspace,'synthetic-tool','{}','pending',now(),now()+interval '1 hour')"), {"id": uuid.uuid4(), "token": token, "user": owner, "workspace": workspace})
            await connection.execute(text("INSERT INTO loans(id,workspace_id,user_id,name,principal,annual_rate,term_months,first_due_date,currency) VALUES (:id,:workspace,:user,'synthetic-loan',100,5,12,current_date,'USD')"), {"id": uuid.uuid4(), "workspace": workspace, "user": owner})
            assert tuple((await connection.execute(text("SELECT paid_installments,archived,version FROM loans"))).one()) == (0, False, 1)
        invalid = [
            ("UPDATE loans SET principal=0", {}),
            ("UPDATE loans SET annual_rate=61", {}),
            ("UPDATE loans SET term_months=601", {}),
            ("UPDATE loans SET paid_installments=13", {}),
            ("UPDATE loans SET version=0", {}),
            ("UPDATE mcp_approvals SET token_id=:id", {"id": uuid.uuid4()}),
            ("UPDATE external_mcp_tokens SET workspace_id=:id", {"id": uuid.uuid4()}),
        ]
        for statement, params in invalid:
            try:
                async with isolated.begin() as connection:
                    await connection.execute(text(statement), params)
            except IntegrityError:
                pass
            else:
                raise AssertionError("Expected database constraint rejection")
        async with isolated.connect() as connection:
            for table in ("users", "workspaces", "external_mcp_tokens", "mcp_approvals", "loans"):
                assert await connection.scalar(text(f'SELECT count(*) FROM "{table}"')) == 1
            indexes = set((await connection.execute(text("SELECT indexname FROM pg_indexes WHERE schemaname=:schema"), {"schema": schema})).scalars())
            assert {"ix_external_mcp_tokens_user_id", "ix_external_mcp_tokens_workspace_id", "ix_mcp_approvals_token_id", "ix_mcp_approvals_user_id", "ix_mcp_approvals_workspace_id", "ix_loans_workspace_id"} <= indexes
        print("PASS: populated 094-096 migration preserves legacy values; DDL failure rolls back; auth/loan defaults, indexes and seven constraint failures verified")
    finally:
        await isolated.dispose()
        async with engine.begin() as connection:
            await connection.execute(text(f'DROP SCHEMA IF EXISTS "{schema}" CASCADE'))
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
