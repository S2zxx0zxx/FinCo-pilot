import hashlib
import json
from pathlib import Path
import subprocess
import sys

import pytest

from scripts.verify_legacy_migration_sources import MigrationSourceError, verify_sources


@pytest.fixture
def source(tmp_path):
    content = b"-- synthetic\nCREATE TABLE synthetic (id INTEGER);\n"
    name = "001_synthetic.sql"
    (tmp_path / name).write_bytes(content)
    return tmp_path, [{"filename": name, "checksum": hashlib.sha256(content).hexdigest()}]


def test_exact_applied_source_is_verified_without_executing_sql(source):
    root, history = source
    result = verify_sources(history, root)
    assert result["all_applied_sources_verified"] is True
    assert result["sql_executed"] is False
    assert result["conversion_ready"] is False
    assert result["original_byte_matches"] == 1
    assert list(root.iterdir()) == [root / "001_synthetic.sql"]


def test_deployed_crlf_bytes_are_reconstructed_exactly(source):
    root, history = source
    content = (root / history[0]["filename"]).read_bytes().replace(b"\n", b"\r\n")
    history[0]["checksum"] = hashlib.sha256(content).hexdigest()
    result = verify_sources(history, root)
    assert result["line_ending_reconstructions"] == 1
    assert result["migrations"][0]["reconstruction"] == "CRLF_bytes"
    assert result["migrations"][0]["recorded_sha256"] == hashlib.sha256(content).hexdigest()


def test_unapplied_sql_is_reported_and_not_run(source):
    root, history = source
    (root / "002_pending.sql").write_text("DROP TABLE synthetic;")
    result = verify_sources(history, root)
    assert result["source_sql_not_in_applied_history"] == ["002_pending.sql"]
    assert result["applied_count"] == 1
    assert result["sql_executed"] is False


@pytest.mark.parametrize("change", ["missing", "different_sql", "checksum", "duplicate", "empty", "no_checksum"])
def test_invalid_or_unrecovered_history_fails_closed(source, change):
    root, history = source
    if change == "missing":
        (root / history[0]["filename"]).unlink()
    elif change == "different_sql":
        (root / history[0]["filename"]).write_text("SELECT 999;")
    elif change == "checksum":
        history[0]["checksum"] = "not-a-sha"
    elif change == "duplicate":
        history.append(dict(history[0]))
    elif change == "empty":
        history = []
    else:
        history[0].pop("checksum")
    with pytest.raises(MigrationSourceError):
        verify_sources(history, root)


@pytest.mark.parametrize("name", ["../001_private.sql", "/tmp/001_private.sql", "001_private.sql/other", "001;command.sql"])
def test_history_filename_cannot_escape_directory(source, name):
    root, history = source
    history[0]["filename"] = name
    with pytest.raises(MigrationSourceError):
        verify_sources(history, root)


def test_symlink_to_outside_source_directory_is_rejected(source, tmp_path):
    root, history = source
    elsewhere = tmp_path / "outside"
    elsewhere.mkdir()
    target = elsewhere / "copied.sql"
    target.write_bytes((root / history[0]["filename"]).read_bytes())
    (root / history[0]["filename"]).unlink()
    (root / history[0]["filename"]).symlink_to(target)
    with pytest.raises(MigrationSourceError):
        verify_sources(history, root)


def test_cli_failure_never_exports_raw_history_or_source(source):
    root, history = source
    history[0]["checksum"] = "private-never-return-this"
    file = root / "history.json"
    file.write_text(json.dumps(history))
    result = subprocess.run([sys.executable, "scripts/verify_legacy_migration_sources.py", str(file), str(root)],
                            cwd=Path(__file__).parents[1], capture_output=True, text=True, timeout=10)
    assert result.returncode == 1
    assert "private-never-return-this" not in result.stdout + result.stderr
    assert json.loads(result.stdout)["sql_executed"] is False
