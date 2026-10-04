"""Security/failure invariants; real pg/restic integration is the disposable CI proof."""

import io
import json
import tarfile
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock

import pytest
from app.services import disaster_recovery as dr
from app.core.restore_quarantine import assert_runtime_target, check_quarantine


@pytest.mark.parametrize(
    "key", ["", "../secret", "/etc/passwd", "a/../b", "a//b", "a\\b", "a\nkey", "./data"]
)
def test_unsafe_keys_rejected(key):
    with pytest.raises(dr.RecoveryError):
        dr.safe_key(key)


def bundle(tmp_path, changes=None):
    root = tmp_path / "source"
    root.mkdir()
    (root / "database.dump").write_bytes(b"Synthetic database dump")
    manifest = {
        "format": dr.TAG,
        "data_key_ids": dr.key_ids(),
        "tables": {},
        "alembic_heads": ["098"],
        "files": [
            {
                "path": "database.dump",
                "size": (root / "database.dump").stat().st_size,
                "sha256": dr.sha_file(root / "database.dump"),
            }
        ],
    }
    if changes:
        changes(manifest)
    (root / "manifest.json").write_text(json.dumps(manifest))
    archive_path = tmp_path / "bundle.tar"
    with tarfile.open(archive_path, "w") as archive:
        for name in ("manifest.json", "database.dump"):
            archive.add(root / name, arcname=name)
    return root, archive_path


def test_bundle_roundtrip_and_corruption_rejection(tmp_path):
    root, path = bundle(tmp_path)
    target = tmp_path / "restored"
    target.mkdir()
    assert dr.unpack(path, target)["format"] == dr.TAG
    (root / "database.dump").write_bytes(b"corrupt")
    with pytest.raises(dr.RecoveryError, match="checksum or size"):
        dr.verify_manifest(root)


@pytest.mark.parametrize("kind", ["traversal", "link", "duplicate", "unknown", "oversized"])
def test_archive_extract_rejects_unsafe_members_without_escape(tmp_path, monkeypatch, kind):
    path = tmp_path / "bad.tar"
    monkeypatch.setattr(dr, "MAX_BUNDLE_BYTES", 10)
    with tarfile.open(path, "w") as archive:
        entry = tarfile.TarInfo("../escape" if kind == "traversal" else "database.dump")
        if kind == "link":
            entry.type = tarfile.SYMTYPE
            entry.linkname = "/etc/passwd"
            archive.addfile(entry)
        else:
            if kind == "unknown":
                entry.name = "unknown"
            data = b"x" * (11 if kind == "oversized" else 1)
            entry.size = len(data)
            archive.addfile(entry, io.BytesIO(data))
            if kind == "duplicate":
                archive.addfile(entry, io.BytesIO(data))
    target = tmp_path / "restored"
    target.mkdir()
    with pytest.raises(dr.RecoveryError):
        dr.unpack(path, target)
    assert not (tmp_path / "escape").exists()


def test_missing_key_and_duplicate_file_manifest_refused(tmp_path):
    root, _ = bundle(tmp_path, lambda m: m.update(data_key_ids=["0" * 64]))
    with pytest.raises(dr.RecoveryError, match="decryption key"):
        dr.verify_manifest(root)
    manifest = json.loads((root / "manifest.json").read_text())
    manifest["data_key_ids"] = dr.key_ids()
    manifest["files"] *= 2
    (root / "manifest.json").write_text(json.dumps(manifest))
    with pytest.raises(dr.RecoveryError, match="duplicate"):
        dr.verify_manifest(root)


def test_absolute_retention_does_not_keep_expired_latest_or_unrelated_snapshots():
    now = datetime(2026, 10, 4, tzinfo=timezone.utc)

    def row(number, age, **changes):
        return {
            "id": str(number) * 64,
            "time": (now - timedelta(days=age)).isoformat(),
            "tags": [dr.TAG],
            "hostname": dr.HOST,
        } | changes

    rows = [row(1, 31), row(2, 30), row(3, 29), row(4, 100, tags=["unrelated"])]
    assert dr.expired_snapshots(rows, now) == ["1" * 64, "2" * 64]
    assert dr.expired_snapshots([row(1, 100)], now) == ["1" * 64]
    with pytest.raises(dr.RecoveryError):
        dr.expired_snapshots([row(1, -1)], now)


def test_libpq_target_overrides_cannot_redirect_restore(monkeypatch):
    monkeypatch.setenv("PGSERVICE", "dangerous")
    monkeypatch.setenv("PGOPTIONS", "-c search_path=other")
    env = dr.pg_env("postgresql+asyncpg://safe:synthetic-secret@localhost:5432/fresh")
    assert env["PGDATABASE"] == "fresh" and env["PGUSER"] == "safe"
    assert "PGSERVICE" not in env and "PGOPTIONS" not in env


def test_restic_credentials_require_private_file(tmp_path, monkeypatch):
    password = tmp_path / "password"
    password.write_text("Synthetic-restic-password")
    monkeypatch.setenv("RESTIC_REPOSITORY", str(tmp_path / "repo"))
    monkeypatch.setenv("RESTIC_PASSWORD_FILE", str(password))
    password.chmod(0o644)
    with pytest.raises(dr.RecoveryError):
        dr.restic_env()
    password.chmod(0o600)
    assert dr.restic_env()["RESTIC_PASSWORD_FILE"] == str(password)
    monkeypatch.setenv("RESTIC_INSECURE_TLS", "true")
    with pytest.raises(dr.RecoveryError):
        dr.restic_env()


@pytest.mark.parametrize("state", [None, False, True])
def test_quarantine_persistent_marker_fails_closed_even_after_database_rename(state):
    connection = MagicMock()
    cursor = connection.cursor.return_value
    cursor.fetchone.side_effect = [
        ("finco_restore_quarantine",),
        None if state is None else (state,),
    ]
    if state is True:
        check_quarantine(connection, None)
    else:
        with pytest.raises(RuntimeError, match="quarantined"):
            check_quarantine(connection, None)
    cursor.close.assert_called_once()


def test_ordinary_target_is_allowed_but_restore_name_is_blocked():
    assert_runtime_target("fincopilot")
    with pytest.raises(RuntimeError):
        assert_runtime_target("finco_restore_" + "a" * 32)
    connection = MagicMock()
    connection.cursor.return_value.fetchone.return_value = (None,)
    check_quarantine(connection, None)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "target",
    ["postgresql://safe:secret@db/fincopilot", "postgresql://safe:secret@db/finco_restore_short"],
)
async def test_restore_never_accepts_normal_database_or_short_marker(target, tmp_path):
    with pytest.raises(dr.RecoveryError, match="isolated"):
        await dr.restore("a" * 64, target, tmp_path / "restore")
    assert not (tmp_path / "restore").exists()


def test_subprocess_failure_never_echoes_secret(monkeypatch):
    def fail(*args, **kwargs):
        raise OSError("postgresql://secret:password@example.com/private")

    monkeypatch.setattr(dr.subprocess, "run", fail)
    with pytest.raises(dr.RecoveryError) as error:
        dr.run(["pg_dump"])
    assert "password" not in str(error.value) and "example.com" not in str(error.value)
