"""Real pg_dump -> encrypted restic -> fresh restricted PostgreSQL restore.

All DBs/roles/files created here are random, synthetic and disposable CI only.
"""

import asyncio
import os
import tempfile
import uuid
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.main import app  # noqa: F401 registers models
from app.agents.config import get_agent_settings
from app.agents.models.agent import Agent
from app.agents.models.knowledge import KnowledgeDoc
from app.core.auth import UserManager, get_jwt_strategy
from app.core.recovery_evidence import evaluate, initialise
from fastapi_users.db import SQLAlchemyUserDatabase
from app.core.config import get_settings
from app.core.database_runtime import create_database_engine
from app.models.account import Account
from app.models.invoice import InvoiceSettings
from app.models.mcp_token import ExternalMCPToken
from app.models.transaction import Transaction
from app.models.transaction_attachment import TransactionAttachment
from app.models.user import User
from app.models.workspace import Workspace, WorkspaceMember
from app.providers.local_storage import LocalStorageProvider
from app.services import disaster_recovery as dr


async def main():
    if os.environ.get("CI") != "true" or os.environ.get("FINCO_DISPOSABLE_DB_TEST") != "yes":
        raise SystemExit("Refusing restore proof outside disposable CI")
    os.umask(0o077)
    settings = get_settings()
    original_url = settings.database_url
    original_storage = settings.storage_local_path
    original_knowledge = get_agent_settings().knowledge_storage_path
    admin = create_database_engine(settings, short_lived=True)
    nonce = uuid.uuid4().hex
    source_name, target_name, role = (
        "finco_backup_" + nonce,
        "finco_restore_" + nonce,
        "finco_dr_" + nonce,
    )
    created = []
    source_engine = target_engine = None
    source_url = dr.make_url(original_url).set(database=source_name)
    target_url = dr.make_url(original_url).set(
        database=target_name, username=role, password="Synthetic-restore-password"
    )
    try:
        async with admin.connect() as connection:
            connection = await connection.execution_options(isolation_level="AUTOCOMMIT")
            await connection.execute(
                text(
                    f"CREATE ROLE \"{role}\" LOGIN PASSWORD 'Synthetic-restore-password' NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION"
                )
            )
            for name, owner in (
                (source_name, dr.make_url(original_url).username),
                (target_name, role),
            ):
                await connection.execute(
                    text(f'CREATE DATABASE "{name}" OWNER {dr.identifier(str(owner))}')
                )
                created.append(name)
            await connection.execute(
                text(f"COMMENT ON DATABASE \"{target_name}\" IS 'FINCO_ISOLATED_RESTORE_V1'")
            )
        # Extension provisioning is an admin-only infrastructure step, not a
        # permission granted to the restore process.
        target_admin_url = dr.make_url(original_url).set(database=target_name)
        provision = create_database_engine(
            settings.model_copy(
                update={"database_url": target_admin_url.render_as_string(hide_password=False)}
            ),
            isolated_restore=True,
        )
        async with provision.begin() as connection:
            await connection.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        await provision.dispose()
        settings.database_url = source_url.render_as_string(hide_password=False)
        migration_env = dict(os.environ, DATABASE_URL=settings.database_url)
        dr.run(["alembic", "upgrade", "head"], env=migration_env)
        source_engine = create_database_engine(settings, short_lived=True)
        sessions = async_sessionmaker(source_engine, expire_on_commit=False)
        with tempfile.TemporaryDirectory(prefix="finco-dr-proof-") as directory:
            root = Path(directory)
            settings.storage_local_path = str(root / "source-objects")
            get_agent_settings().knowledge_storage_path = str(root / "source-knowledge")
            Path(get_agent_settings().knowledge_storage_path).mkdir()
            os.environ["RESTIC_REPOSITORY"] = str(root / "encrypted-repository")
            password = root / "restic-password"
            password.write_text("Synthetic-private-restic-password")
            os.environ["RESTIC_PASSWORD_FILE"] = str(password)
            dr.run(["restic", "init"], env=dr.restic_env())
            storage = LocalStorageProvider()
            user_id, workspace_id, account_id, tx_id, doc_id, logo_id = [
                uuid.uuid4() for _ in range(6)
            ]
            key = f"{workspace_id}/{tx_id}/receipt.bin"
            payload, knowledge, logo = (
                b"Synthetic attachment\x00exact bytes",
                b"Synthetic knowledge bytes",
                b"Synthetic logo bytes",
            )
            await storage.upload(key, payload, "application/octet-stream")
            logo_key = f"{workspace_id}/invoices/logo/{logo_id}.png"
            await storage.upload(logo_key, logo, "image/png")
            knowledge_path = (
                Path(get_agent_settings().knowledge_storage_path) / f"{doc_id}__proof.txt"
            )
            knowledge_path.write_bytes(knowledge)
            async with sessions() as session:
                user = User(
                    id=user_id,
                    email="restore-proof@example.com",
                    hashed_password="synthetic-hash",
                    is_active=True,
                    is_verified=True,
                    is_superuser=False,
                    auth_epoch="before-backup",
                    is_2fa_enabled=True,
                    totp_secret="JBSWY3DPEHPK3PXP",
                )
                session.add(user)
                await session.flush()
                session.add(
                    Workspace(
                        id=workspace_id,
                        name="Synthetic restore workspace",
                        created_by_user_id=user_id,
                        billing_owner_user_id=user_id,
                    )
                )
                await session.flush()
                session.add(
                    WorkspaceMember(workspace_id=workspace_id, user_id=user_id, role="owner")
                )
                session.add(
                    Account(
                        id=account_id,
                        user_id=user_id,
                        workspace_id=workspace_id,
                        name="Synthetic wallet",
                        type="checking",
                        balance=Decimal("10000.42"),
                        currency="INR",
                    )
                )
                await session.flush()
                session.add(
                    Transaction(
                        id=tx_id,
                        user_id=user_id,
                        workspace_id=workspace_id,
                        account_id=account_id,
                        description="Synthetic purchase",
                        amount=Decimal("123.45"),
                        currency="INR",
                        date=date(2026, 10, 4),
                        effective_date=date(2026, 10, 4),
                        type="debit",
                        source="manual",
                    )
                )
                agent = Agent(user_id=user_id, workspace_id=workspace_id, name="Synthetic agent")
                session.add(agent)
                await session.flush()
                session.add(
                    TransactionAttachment(
                        transaction_id=tx_id,
                        user_id=user_id,
                        workspace_id=workspace_id,
                        filename="receipt.bin",
                        storage_key=key,
                        size=len(payload),
                        content_type="application/octet-stream",
                    )
                )
                session.add(
                    KnowledgeDoc(
                        id=doc_id,
                        agent_id=agent.id,
                        user_id=user_id,
                        title="Proof",
                        mime="text/plain",
                        storage_path=str(knowledge_path),
                        size_bytes=len(knowledge),
                    )
                )
                session.add(InvoiceSettings(workspace_id=workspace_id, logo_id=logo_id))
                session.add(
                    ExternalMCPToken(
                        user_id=user_id,
                        workspace_id=workspace_id,
                        credential_stamp="a" * 64,
                        allow_writes=False,
                        expires_at=datetime.now(timezone.utc) + timedelta(days=1),
                    )
                )
                await session.commit()
                old_session_token = await get_jwt_strategy().write_token(user)
            before = await dr.backup(storage)
            assert before["files"] == 3
            # Demonstrate point-in-time snapshot, never alter source to recover.
            async with sessions() as session:
                await session.execute(text("UPDATE accounts SET balance=54321.99"))
                await session.commit()
            report = await dr.restore(
                before["snapshot_id"],
                target_url.render_as_string(hide_password=False),
                root / "recovery",
            )
            assert (
                report["status"] == "quarantined_restore_verified"
                and report["automatic_release"] is False
            )
            case = root / "recovery-case"
            initialise(
                root / "recovery/restore-report.json",
                case,
                incident_id="ci-rehearsal",
                app_commit=os.environ["GITHUB_SHA"],
                incident_at=report["restore_started_at"],
                exercise_kind="synthetic",
            )
            evidence = evaluate(case)
            assert evidence["status"] == "incomplete" and len(evidence["missing_gates"]) == 10
            assert evidence["automatic_release"] is False and evidence["rto_measured"] is False
            assert report["restore_elapsed_seconds"] >= 0
            print(
                "PASS: recovery case binds actual restore report; ten missing gates block completion; no automatic promotion or RTO claim"
            )
            target_settings = settings.model_copy(
                update={"database_url": target_url.render_as_string(hide_password=False)}
            )
            target_engine = create_database_engine(
                target_settings, short_lived=True, isolated_restore=True
            )
            async with async_sessionmaker(target_engine)() as session:
                restored = await session.get(User, user_id)
                assert (
                    restored is not None
                    and restored.totp_secret == "JBSWY3DPEHPK3PXP"
                    and restored.is_2fa_enabled
                )
                assert restored.auth_epoch != "before-backup"
                assert (
                    await get_jwt_strategy().read_token(
                        old_session_token, UserManager(SQLAlchemyUserDatabase(session, User))
                    )
                    is None
                )
                assert await session.scalar(
                    select(Account.balance).where(Account.id == account_id)
                ) == Decimal("10000.42")
                assert await session.scalar(select(ExternalMCPToken.revoked)) is True
                restored_doc = await session.get(KnowledgeDoc, doc_id)
                assert (
                    restored_doc is not None
                    and restored_doc.storage_path is not None
                    and Path(restored_doc.storage_path).read_bytes() == knowledge
                )
            assert (root / "recovery/object-storage" / key).read_bytes() == payload
            assert (root / "recovery/object-storage" / logo_key).read_bytes() == logo
            async with sessions() as session:
                assert await session.scalar(select(Account.balance)) == Decimal("54321.99")
            # Prefix gate plus persistent marker after an actual DB rename.
            try:
                create_database_engine(target_settings)
            except RuntimeError:
                pass
            else:
                raise AssertionError("Quarantine name accepted by runtime")
            await target_engine.dispose()
            recovered_name = "finco_recovered_" + nonce
            async with admin.connect() as connection:
                connection = await connection.execution_options(isolation_level="AUTOCOMMIT")
                await connection.execute(
                    text(f'ALTER DATABASE "{target_name}" RENAME TO "{recovered_name}"')
                )
            created[-1] = recovered_name
            renamed_settings = target_settings.model_copy(
                update={
                    "database_url": target_url.set(database=recovered_name).render_as_string(
                        hide_password=False
                    )
                }
            )
            runtime = create_database_engine(renamed_settings, short_lived=True)
            try:
                async with runtime.connect():
                    raise AssertionError("Renamed quarantine database accepted by runtime")
            except RuntimeError as exc:
                assert "quarantined" in str(exc)
            finally:
                await runtime.dispose()
            dr.run(["restic", "check", "--read-data"], env=dr.restic_env())
            print(
                "PASS: full migrated PostgreSQL dump -> encrypted Restic -> fresh restricted-role restore; all table fingerprints/files exact; MFA preserved; sessions/MCP invalidated; source unchanged; runtime quarantine blocks"
            )
            # Wrong-key read must fail without printing the credential.
            wrong = root / "wrong-password"
            wrong.write_text("Synthetic-wrong-restic-password")
            wrong_env = dict(dr.restic_env(), RESTIC_PASSWORD_FILE=str(wrong))
            try:
                dr.run(["restic", "snapshots", "--json"], env=wrong_env)
            except dr.RecoveryError:
                pass
            else:
                raise AssertionError("Wrong repository password accepted")
            # Actual expiry removes only our 31-day-old synthetic snapshot.
            old_time = (datetime.now(timezone.utc) - timedelta(days=31)).strftime(
                "%Y-%m-%d %H:%M:%S"
            )
            old_payload = root / "old-retention-payload"
            old_payload.write_bytes(b"Synthetic old retention snapshot")
            with old_payload.open("rb") as stream:
                dr.run(
                    [
                        "restic",
                        "backup",
                        "--stdin",
                        "--stdin-filename",
                        dr.BUNDLE,
                        "--host",
                        dr.HOST,
                        "--tag",
                        dr.TAG,
                        "--time",
                        old_time,
                        "--json",
                    ],
                    env=dr.restic_env(),
                    stdin=stream,
                )
            assert dr.expire()["expired_snapshots"] == 1
            assert dr.expire(apply=True)["expired_snapshots"] == 1
            assert dr.expire()["expired_snapshots"] == 0
            print(
                "PASS: real encrypted repository wrong-key access denied; 31-day snapshot forgotten/pruned while current snapshot retained"
            )

    finally:
        settings.database_url = original_url
        settings.storage_local_path = original_storage
        get_agent_settings().knowledge_storage_path = original_knowledge
        for engine in (source_engine, target_engine):
            if engine is not None:
                await engine.dispose()
        async with admin.connect() as connection:
            connection = await connection.execution_options(isolation_level="AUTOCOMMIT")
            for name in created:
                await connection.execute(text(f'DROP DATABASE IF EXISTS "{name}" WITH (FORCE)'))
            await connection.execute(text(f'DROP ROLE IF EXISTS "{role}"'))
        await admin.dispose()


if __name__ == "__main__":
    asyncio.run(main())
