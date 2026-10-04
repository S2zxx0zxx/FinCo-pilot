"""Operator-only encrypted database/file backups and quarantined recovery.

No application route; no production overwrite or automatic release operation.
Restic owns authenticated encryption. PostgreSQL owns dump/restore semantics.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import tarfile
import tempfile
import time
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.engine import make_url

from app.core.config import get_settings
from app.core.credential_keys import data_keys
from app.core.database_runtime import create_database_engine
from app.core.retention import BACKUP_MAX_RETENTION_DAYS

TAG = "finco-dr-v1"
HOST = "fincopilot"
BUNDLE = "finco-dr.bundle"
MAX_FILES = 100_000
MAX_BUNDLE_BYTES = 100 * 1024**3
MAX_FILE_BYTES = 1024**3
HEX64 = re.compile(r"[a-f0-9]{64}\Z")


class RecoveryError(RuntimeError):
    """Bounded errors must never expose provider output or credentials."""


def safe_key(key: str) -> str:
    if (
        not isinstance(key, str)
        or not key
        or len(key) > 500
        or key.startswith("/")
        or "\\" in key
        or any(p in {"", ".", ".."} for p in key.split("/"))
        or any(ord(c) < 32 for c in key)
    ):
        raise RecoveryError("Invalid object key")
    return key


def key_ids() -> list[str]:
    return sorted(
        hashlib.sha256(("finco-dr-data-key:" + key).encode()).hexdigest() for key in data_keys()
    )


def sha_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def run(command: list[str], *, env=None, cwd=None, stdin=None, output: Path | None = None) -> str:
    # Bounded diagnostics stay private: pg/restic errors may contain keys/URLs.
    with tempfile.TemporaryFile() as out, tempfile.TemporaryFile() as err:
        try:
            result = subprocess.run(
                command,
                env=env,
                cwd=cwd,
                stdin=stdin,
                stdout=out,
                stderr=err,
                timeout=7200,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired):
            raise RecoveryError("Recovery tool unavailable or timed out") from None
        if result.returncode != 0:
            raise RecoveryError("Recovery tool failed; no successful checkpoint recorded")
        out.seek(0)
        if output is not None:
            with output.open("xb") as destination:
                while chunk := out.read(1024 * 1024):
                    destination.write(chunk)
            return ""
        value = out.read(8 * 1024 * 1024 + 1)
        if len(value) > 8 * 1024 * 1024:
            raise RecoveryError("Recovery tool output limit exceeded")
        return value.decode("utf-8")


def pg_env(database_url: str) -> dict[str, str]:
    settings = get_settings()
    url = make_url(database_url)
    if url.get_backend_name() != "postgresql" or not url.host or not url.database:
        raise RecoveryError("Explicit PostgreSQL target required")
    # Inherit provider credentials for restic separately; pg never accepts
    # ambient libpq target/service/options that could redirect an operation.
    env = {k: v for k, v in os.environ.items() if not k.startswith("PG")}
    env.update(
        PGHOST=url.host,
        PGPORT=str(url.port or 5432),
        PGDATABASE=url.database,
        PGUSER=url.username or "",
        PGPASSWORD=url.password or "",
        PGSSLMODE=settings.db_ssl_mode,
        PGCONNECT_TIMEOUT="10",
        PGAPPNAME="fincopilot-disaster-recovery",
    )
    if settings.db_ssl_ca_file:
        env["PGSSLROOTCERT"] = settings.db_ssl_ca_file
    elif settings.db_ssl_mode in {"verify-ca", "verify-full"}:
        env["PGSSLROOTCERT"] = "system"
        env["PGSSLMODE"] = "verify-full"
    return env


def restic_env() -> dict[str, str]:
    env = dict(os.environ)
    password = Path(env.get("RESTIC_PASSWORD_FILE", ""))
    if not env.get("RESTIC_REPOSITORY") or not password.is_file() or password.is_symlink():
        raise RecoveryError("Restic repository and private password file required")
    if password.stat().st_mode & 0o077 or password.stat().st_size == 0:
        raise RecoveryError("Restic password file must be nonempty and private")
    if (
        env.get("RESTIC_PASSWORD")
        or env.get("RESTIC_PASSWORD_COMMAND")
        or env.get("RESTIC_INSECURE_TLS")
    ):
        raise RecoveryError("Unsupported restic credential or insecure TLS override")
    if env.get("RESTIC_REPOSITORY_FILE"):
        raise RecoveryError("Ambiguous repository selection")
    if get_settings().is_production and not env["RESTIC_REPOSITORY"].startswith(
        ("s3:https://", "sftp:", "rest:https://")
    ):
        raise RecoveryError(
            "Production backup requires a private off-host repository with secure transport"
        )
    # Repository credentials travel only through environment/private files.
    return env


def identifier(value: str) -> str:
    return '"' + value.replace('"', '""') + '"'


async def inventory(connection) -> dict[str, dict]:
    await connection.execute(text("SET LOCAL TIME ZONE 'UTC'"))
    await connection.execute(text("SET LOCAL extra_float_digits = 3"))
    tables = (
        await connection.execute(
            text("""
        SELECT n.nspname, c.relname FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
        WHERE c.relkind IN ('r','p') AND n.nspname NOT LIKE 'pg_%'
        AND n.nspname <> 'information_schema' ORDER BY 1,2
    """)
        )
    ).all()
    result = {}
    for schema, table in tables:
        qualified = identifier(schema) + "." + identifier(table)
        digest, count = hashlib.sha256(), 0
        rows = await connection.stream(
            text(
                f'SELECT row_to_json(t)::text AS row FROM {qualified} t ORDER BY row_to_json(t)::text COLLATE "C"'
            )
        )
        async for row in rows:
            encoded = row[0].encode()
            digest.update(len(encoded).to_bytes(8, "big"))
            digest.update(encoded)
            count += 1
        result[schema + "." + table] = {"count": count, "sha256": digest.hexdigest()}
    return result


async def referenced_files(connection) -> list[dict]:
    tables = set(
        (
            await connection.execute(
                text("SELECT tablename FROM pg_tables WHERE schemaname='public'")
            )
        ).scalars()
    )
    refs = {}
    for table in ("transaction_attachments", "invoice_attachments"):
        if table in tables:
            for key, size, mime in (
                await connection.execute(
                    text(f"SELECT storage_key, size, content_type FROM {identifier(table)}")
                )
            ).all():
                key = safe_key(key)
                item = {"kind": "object", "key": key, "expected_size": size, "content_type": mime}
                if key in refs and refs[key] != item:
                    raise RecoveryError("Conflicting object references")
                refs[key] = item
    if "invoice_settings" in tables:
        for workspace, logo in (
            await connection.execute(
                text("SELECT workspace_id, logo_id FROM invoice_settings WHERE logo_id IS NOT NULL")
            )
        ).all():
            key = f"{workspace}/invoices/logo/{logo}.png"
            refs[key] = {"kind": "object", "key": key, "content_type": "image/png"}
    if "invoices" in tables:
        for workspace, snapshot in (
            await connection.execute(
                text("SELECT workspace_id, snapshot FROM invoices WHERE snapshot IS NOT NULL")
            )
        ).all():
            logo = (snapshot.get("issuer") or {}).get("logo_id")
            if logo:
                key = f"{workspace}/invoices/logo/{uuid.UUID(str(logo))}.png"
                refs[key] = {"kind": "object", "key": key, "content_type": "image/png"}
    if "agent_knowledge_docs" in tables:
        from app.agents.config import get_agent_settings

        base = Path(get_agent_settings().knowledge_storage_path).resolve()
        for identity, raw, size in (
            await connection.execute(
                text(
                    "SELECT id, storage_path, size_bytes FROM agent_knowledge_docs WHERE storage_path IS NOT NULL"
                )
            )
        ).all():
            path = Path(raw)
            resolved = path.resolve()
            if (
                path.is_symlink()
                or resolved.parent != base
                or not resolved.name.startswith(str(identity) + "__")
            ):
                raise RecoveryError("Invalid knowledge file reference")
            refs["knowledge:" + str(identity)] = {
                "kind": "knowledge",
                "key": safe_key(resolved.name),
                "doc_id": str(identity),
                "source_path": str(resolved),
                "expected_size": size,
            }
    if len(refs) > MAX_FILES:
        raise RecoveryError("File inventory limit exceeded")
    return [refs[k] for k in sorted(refs)]


def verify_manifest(root: Path) -> dict:
    manifest_path = root / "manifest.json"
    if manifest_path.stat().st_size > 32 * 1024 * 1024:
        raise RecoveryError("Manifest size limit exceeded")
    manifest = json.loads(manifest_path.read_text())
    if (
        manifest.get("format") != TAG
        or not manifest.get("data_key_ids")
        or not set(manifest.get("data_key_ids", [])).issubset(key_ids())
    ):
        raise RecoveryError("Unsupported backup or unavailable decryption key ring")
    files = manifest.get("files")
    if not isinstance(files, list) or len(files) > MAX_FILES + 1:
        raise RecoveryError("Invalid file manifest")
    paths = set()
    for entry in files:
        name = safe_key(entry["path"])
        if name in paths or not (name == "database.dump" or re.fullmatch(r"files/[0-9]{6}", name)):
            raise RecoveryError("Invalid or duplicate bundle file")
        paths.add(name)
        path = root / name
        if (
            path.is_symlink()
            or not path.is_file()
            or path.stat().st_size != entry["size"]
            or sha_file(path) != entry["sha256"]
        ):
            raise RecoveryError("Bundle checksum or size mismatch")
        if name != "database.dump":
            safe_key(entry["key"])
            if entry["kind"] not in {"object", "knowledge"}:
                raise RecoveryError("Invalid file kind")
    if "database.dump" not in paths:
        raise RecoveryError("Database dump missing")
    if any(p.is_symlink() for p in root.rglob("*")):
        raise RecoveryError("Symlinks in recovery payload")
    actual = {str(p.relative_to(root)) for p in root.rglob("*") if p.is_file()}
    if actual != paths | {"manifest.json"}:
        raise RecoveryError("Unexpected bundle contents")
    return manifest


def unpack(bundle: Path, root: Path) -> dict:
    # Never extractall: reject links, duplicate names, devices and traversal.
    total, names = 0, set()
    with tarfile.open(bundle, "r:") as archive:
        for member in archive:
            name = safe_key(member.name)
            if (
                not member.isfile()
                or name in names
                or len(names) > MAX_FILES + 1
                or not (
                    name in {"manifest.json", "database.dump"}
                    or re.fullmatch(r"files/[0-9]{6}", name)
                )
            ):
                raise RecoveryError("Unsafe recovery archive")
            total += member.size
            if member.size < 0 or total > MAX_BUNDLE_BYTES:
                raise RecoveryError("Recovery archive size limit exceeded")
            names.add(name)
            path = root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            source = archive.extractfile(member)
            if source is None:
                raise RecoveryError("Unreadable archive member")
            with path.open("xb") as destination:
                while chunk := source.read(1024 * 1024):
                    destination.write(chunk)
    return verify_manifest(root)


async def backup(storage=None) -> dict:
    from app.providers import get_storage_provider

    settings = get_settings()
    env = restic_env()
    storage = storage or get_storage_provider()
    engine = create_database_engine(settings, short_lived=True)
    try:
        with tempfile.TemporaryDirectory(prefix="finco-dr-") as directory:
            root = Path(directory)
            async with engine.connect() as connection:
                connection = await connection.execution_options(isolation_level="REPEATABLE READ")
                async with connection.begin():
                    await connection.execute(text("SET TRANSACTION READ ONLY"))
                    await connection.execute(
                        text("SET LOCAL idle_in_transaction_session_timeout = 0")
                    )
                    captured_at = datetime.now(timezone.utc).isoformat()
                    snapshot = await connection.scalar(text("SELECT pg_export_snapshot()"))
                    tables = await inventory(connection)
                    refs = await referenced_files(connection)
                    run(
                        [
                            "pg_dump",
                            "--format=custom",
                            "--no-password",
                            "--no-comments",
                            "--snapshot=" + str(snapshot),
                            "--file=" + str(root / "database.dump"),
                        ],
                        env=pg_env(settings.database_url),
                    )
                    files = [
                        {
                            "path": "database.dump",
                            "size": (root / "database.dump").stat().st_size,
                            "sha256": sha_file(root / "database.dump"),
                        }
                    ]
                    (root / "files").mkdir()
                    total = files[0]["size"]
                    for index, ref in enumerate(refs):
                        data = (
                            Path(ref["source_path"]).read_bytes()
                            if ref["kind"] == "knowledge"
                            else await storage.download(ref["key"])
                        )
                        if len(data) > MAX_FILE_BYTES or (
                            "expected_size" in ref and len(data) != ref["expected_size"]
                        ):
                            raise RecoveryError("Referenced file size mismatch or limit exceeded")
                        total += len(data)
                        if total > MAX_BUNDLE_BYTES:
                            raise RecoveryError("Backup size limit exceeded")
                        name = f"files/{index:06d}"
                        (root / name).write_bytes(data)
                        files.append(
                            {
                                k: v
                                for k, v in ref.items()
                                if k not in {"source_path", "expected_size"}
                            }
                            | {
                                "path": name,
                                "size": len(data),
                                "sha256": hashlib.sha256(data).hexdigest(),
                            }
                        )
                    revisions = list(
                        (
                            await connection.execute(
                                text("SELECT version_num FROM alembic_version")
                            )
                        ).scalars()
                    )
            manifest = {
                "format": TAG,
                "created_at": captured_at,
                "data_key_ids": key_ids(),
                "alembic_heads": sorted(revisions),
                "tables": tables,
                "files": files,
            }
            (root / "manifest.json").write_text(json.dumps(manifest, sort_keys=True))
            bundle = root / BUNDLE
            with tarfile.open(bundle, "w") as archive:
                for name in ["manifest.json", *[f["path"] for f in files]]:
                    archive.add(root / str(name), arcname=str(name), recursive=False)
            with bundle.open("rb") as stream:
                output = run(
                    [
                        "restic",
                        "backup",
                        "--stdin",
                        "--stdin-filename",
                        BUNDLE,
                        "--host",
                        HOST,
                        "--tag",
                        TAG,
                        "--json",
                    ],
                    env=env,
                    stdin=stream,
                )
            summaries = [json.loads(line) for line in output.splitlines() if line.strip()]
            snapshots = [
                r["snapshot_id"]
                for r in summaries
                if r.get("message_type") == "summary" and r.get("snapshot_id")
            ]
            if len(snapshots) != 1 or not HEX64.fullmatch(snapshots[0]):
                raise RecoveryError("Backup completion ID missing")
            return {
                "status": "encrypted_backup_created_restore_not_proven",
                "snapshot_id": snapshots[0],
                "created_at": manifest["created_at"],
                "tables": len(tables),
                "files": len(refs),
            }
    finally:
        await engine.dispose()


def expired_snapshots(snapshots: list[dict], now: datetime) -> list[str]:
    cutoff = now - timedelta(days=BACKUP_MAX_RETENTION_DAYS)
    expired = []
    for row in snapshots:
        if TAG not in row.get("tags", []) or row.get("hostname") != HOST:
            continue
        identity = row.get("id", "")
        created = datetime.fromisoformat(row["time"].replace("Z", "+00:00"))
        if (
            not HEX64.fullmatch(identity)
            or created.tzinfo is None
            or created > now + timedelta(minutes=5)
        ):
            raise RecoveryError("Invalid snapshot retention metadata")
        if created <= cutoff:
            expired.append(identity)
    return expired


def expire(*, apply: bool = False) -> dict:
    env = restic_env()
    rows = json.loads(run(["restic", "snapshots", "--tag", TAG, "--host", HOST, "--json"], env=env))
    ids = expired_snapshots(rows, datetime.now(timezone.utc))
    if apply and ids:
        run(["restic", "forget", *ids], env=env)
        run(["restic", "prune"], env=env)
        run(["restic", "check"], env=env)
    return {
        "status": "expired" if apply else "dry_run",
        "expired_snapshots": len(ids),
        "retention_days": BACKUP_MAX_RETENTION_DAYS,
    }


async def restore(snapshot_id: str, database_url: str, destination: Path) -> dict:
    started_at = datetime.now(timezone.utc)
    started_clock = time.monotonic()
    if not HEX64.fullmatch(snapshot_id):
        raise RecoveryError("Exact snapshot ID required")
    target = make_url(database_url)
    source = make_url(get_settings().database_url)
    if not re.fullmatch(r"finco_restore_[a-f0-9]{32}", target.database or "") or (
        target.host,
        target.port or 5432,
        target.database,
    ) == (source.host, source.port or 5432, source.database):
        raise RecoveryError("Fresh isolated restore database required")
    if destination.exists() or destination.is_symlink():
        raise RecoveryError("Restore directory must not exist")
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.mkdir(mode=0o700)
    env = restic_env()
    settings = get_settings().model_copy(update={"database_url": database_url, "debug": False})
    engine = create_database_engine(settings, short_lived=True, isolated_restore=True)
    try:
        async with engine.begin() as connection:
            actual = await connection.scalar(text("SELECT current_database()"))
            marked = await connection.scalar(
                text(
                    "SELECT shobj_description(oid, 'pg_database') FROM pg_database WHERE datname=current_database()"
                )
            )
            elevated = await connection.scalar(
                text(
                    "SELECT rolsuper OR rolcreatedb OR rolcreaterole OR rolreplication FROM pg_roles WHERE rolname=current_user"
                )
            )
            count = await connection.scalar(
                text(
                    "SELECT count(*) FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace WHERE c.relkind IN ('r','p','v','m','S','f') AND n.nspname NOT LIKE 'pg_%' AND n.nspname <> 'information_schema'"
                )
            )
            if (
                actual != target.database
                or marked != "FINCO_ISOLATED_RESTORE_V1"
                or elevated
                or count
            ):
                raise RecoveryError(
                    "Restore target must be marked, empty and use a nonprivileged role"
                )
            # Persistent marker remains even if restore or later validation fails.
            await connection.execute(
                text(
                    "CREATE TABLE public.finco_restore_quarantine (singleton boolean PRIMARY KEY CHECK(singleton), released boolean NOT NULL DEFAULT false)"
                )
            )
            await connection.execute(
                text("INSERT INTO public.finco_restore_quarantine(singleton) VALUES (true)")
            )
        with tempfile.TemporaryDirectory(prefix="finco-dr-read-") as directory:
            root = Path(directory)
            bundle = root / BUNDLE
            run(["restic", "dump", snapshot_id, BUNDLE], env=env, output=bundle)
            if bundle.stat().st_size > MAX_BUNDLE_BYTES:
                raise RecoveryError("Encrypted backup payload exceeds configured limit")
            payload = root / "payload"
            payload.mkdir(mode=0o700)
            manifest = unpack(bundle, payload)
            run(
                [
                    "pg_restore",
                    "--no-password",
                    "--no-owner",
                    "--no-acl",
                    "--no-tablespaces",
                    "--single-transaction",
                    "--exit-on-error",
                    "--dbname=" + (target.database or ""),
                    str(payload / "database.dump"),
                ],
                env=pg_env(database_url),
            )
            async with engine.begin() as connection:
                observed = await inventory(connection)
                observed.pop("public.finco_restore_quarantine", None)
                if observed != manifest["tables"]:
                    raise RecoveryError("Restored database fingerprint mismatch")
                revisions = sorted(
                    (
                        await connection.execute(text("SELECT version_num FROM alembic_version"))
                    ).scalars()
                )
                if revisions != manifest["alembic_heads"]:
                    raise RecoveryError("Restored migration revision mismatch")
                # Fresh credential epochs prevent resurrecting sessions revoked
                # after the backup. Keep MFA secrets and financial rows intact.
                await connection.execute(
                    text("UPDATE users SET auth_epoch = gen_random_uuid()::text")
                )
                if "public.external_mcp_tokens" in observed:
                    await connection.execute(text("UPDATE external_mcp_tokens SET revoked = true"))
                for entry in manifest["files"]:
                    if entry["path"] == "database.dump":
                        continue
                    folder = "object-storage" if entry["kind"] == "object" else "knowledge"
                    output = destination / folder / safe_key(entry["key"])
                    output.parent.mkdir(parents=True, exist_ok=True)
                    with (
                        (payload / entry["path"]).open("rb") as input_stream,
                        output.open("xb") as output_stream,
                    ):
                        while chunk := input_stream.read(1024 * 1024):
                            output_stream.write(chunk)
                    if sha_file(output) != entry["sha256"]:
                        raise RecoveryError("Restored file checksum mismatch")
                    if entry["kind"] == "knowledge":
                        await connection.execute(
                            text("UPDATE agent_knowledge_docs SET storage_path=:path WHERE id=:id"),
                            {"path": str(output.resolve()), "id": uuid.UUID(entry["doc_id"])},
                        )
            report = {
                "format": "finco-restore-report-v1",
                "status": "quarantined_restore_verified",
                "snapshot_id": snapshot_id,
                "backup_created_at": manifest["created_at"],
                "restore_started_at": started_at.isoformat(),
                "restore_completed_at": datetime.now(timezone.utc).isoformat(),
                "restore_elapsed_seconds": round(time.monotonic() - started_clock, 3),
                "target_identity_sha256": hashlib.sha256(
                    json.dumps([target.host, target.port or 5432, target.database]).encode()
                ).hexdigest(),
                "tables": len(observed),
                "files": len(manifest["files"]) - 1,
                "automatic_release": False,
                "release_gates": [
                    "fresh_deletion_ledger_and_legal_holds",
                    "payment_provider_reconciliation",
                    "isolated_object_store_population",
                    "encryption_keys_and_fresh_redis",
                    "operator_review_and_runtime_checks",
                ],
            }
            (destination / "restore-report.json").write_text(json.dumps(report, indent=2))
            return report
    finally:
        await engine.dispose()
