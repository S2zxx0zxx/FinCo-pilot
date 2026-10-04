import hashlib
import json
from datetime import datetime, timezone

import pytest

from app.core import recovery_evidence as evidence


NOW = datetime(2026, 10, 4, 16, tzinfo=timezone.utc)


@pytest.fixture
def case(tmp_path):
    report = {
        "format": "finco-restore-report-v1",
        "status": "quarantined_restore_verified",
        "snapshot_id": "a" * 64,
        "target_identity_sha256": "b" * 64,
        "backup_created_at": "2026-10-04T12:00:00Z",
        "restore_started_at": "2026-10-04T13:00:00Z",
        "restore_completed_at": "2026-10-04T13:01:00Z",
        "restore_elapsed_seconds": 60.0,
        "tables": 10,
        "files": 3,
        "automatic_release": False,
        "release_gates": [
            "fresh_deletion_ledger_and_legal_holds",
            "payment_provider_reconciliation",
            "isolated_object_store_population",
            "encryption_keys_and_fresh_redis",
            "operator_review_and_runtime_checks",
        ],
    }
    directory = tmp_path / "case"
    directory.mkdir(mode=0o700)
    data = json.dumps(report).encode()
    (directory / "restore-report.json").write_bytes(data)
    record = {
        "format": "finco-recovery-case-v1",
        "exercise_kind": "synthetic",
        "incident_id": "drill-1",
        "app_commit": "c" * 40,
        "incident_at": "2026-10-04T12:30:00Z",
        "restore_report_sha256": hashlib.sha256(data).hexdigest(),
        "gates": {},
    }
    (directory / "case.json").write_text(json.dumps(record))
    for path in directory.iterdir():
        path.chmod(0o600)
    return directory, record, report


def write_case(directory, record):
    (directory / "case.json").write_text(json.dumps(record))


def test_missing_gates_and_rpo_are_not_rto_or_promotion(case):
    directory, _, _ = case
    result = evidence.evaluate(directory, now=NOW)
    assert result["missing_gates"] == list(evidence.GATES)
    assert result["status"] == "incomplete"
    assert result["recovery_point_age_at_incident_seconds"] == 1800
    assert result["rto_measured"] is False and result["automatic_release"] is False


def test_complete_hashed_documents_are_explicitly_not_live_proof_or_promotion(case):
    directory, record, _ = case
    for gate in evidence.GATES:
        data = ("Synthetic evidence for " + gate).encode()
        path = directory / (gate + ".txt")
        path.write_bytes(data)
        path.chmod(0o600)
        record["gates"][gate] = {
            "artifact": path.name,
            "sha256": hashlib.sha256(data).hexdigest(),
            "verified_at": "2026-10-04T13:02:00Z",
            "reviewer_id": "operator-1",
        }
    write_case(directory, record)
    result = evidence.evaluate(directory, now=NOW)
    assert result["status"] == "documented_gates_complete_not_promoted"
    assert result["exercise_kind"] == "synthetic" and result["automatic_release"] is False
    (directory / "keys.txt").write_text("changed evidence")
    with pytest.raises(evidence.EvidenceError, match="checksum"):
        evidence.evaluate(directory, now=NOW)


@pytest.mark.parametrize(
    "mutation", ["unknown", "traversal", "bool", "stale", "future", "extra", "reserved"]
)
def test_malformed_or_stale_gate_refused(case, mutation):
    directory, record, _ = case
    path = directory / "gate.txt"
    path.write_text("Synthetic evidence")
    path.chmod(0o600)
    gate = {
        "artifact": "gate.txt",
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "verified_at": "2026-10-04T13:02:00Z",
        "reviewer_id": "operator-1",
    }
    record["gates"]["unknown" if mutation == "unknown" else "keys"] = gate
    if mutation == "traversal":
        gate["artifact"] = "../gate.txt"
    if mutation == "bool":
        gate["sha256"] = True
    if mutation == "stale":
        gate["verified_at"] = "2026-10-04T12:02:00Z"
    if mutation == "future":
        gate["verified_at"] = "2026-10-05T12:02:00Z"
    if mutation == "extra":
        gate["password"] = "synthetic-secret"
    if mutation == "reserved":
        gate["artifact"] = "case.json"
    write_case(directory, record)
    with pytest.raises(ValueError):
        evidence.evaluate(directory, now=NOW)


@pytest.mark.parametrize(
    "mutation", ["binding", "released", "naive", "duration", "chronology", "release_gates"]
)
def test_report_tampering_and_invalid_chronology_refused(case, mutation):
    directory, record, report = case
    if mutation == "released":
        report["automatic_release"] = True
    if mutation == "naive":
        report["restore_started_at"] = "2026-10-04T13:00:00"
    if mutation == "duration":
        report["restore_elapsed_seconds"] = 0.0
    if mutation == "chronology":
        report["backup_created_at"] = "2026-10-04T14:00:00Z"
    if mutation == "release_gates":
        report["release_gates"] = []
    data = json.dumps(report).encode() + (b" " if mutation == "binding" else b"")
    (directory / "restore-report.json").write_bytes(data)
    if mutation != "binding":
        record["restore_report_sha256"] = hashlib.sha256(data).hexdigest()
    write_case(directory, record)
    with pytest.raises(ValueError):
        evidence.evaluate(directory, now=NOW)


def test_private_size_and_symlink_controls(case, tmp_path):
    directory, _, _ = case
    path = directory / "case.json"
    path.chmod(0o644)
    with pytest.raises(evidence.EvidenceError):
        evidence.evaluate(directory, now=NOW)
    path.chmod(0o600)
    link = tmp_path / "link"
    link.symlink_to(directory, target_is_directory=True)
    with pytest.raises(evidence.EvidenceError):
        evidence.evaluate(link, now=NOW)
    path.write_bytes(b"x" * (evidence.MAX_BYTES + 1))
    with pytest.raises(evidence.EvidenceError):
        evidence.evaluate(directory, now=NOW)


def test_init_preserves_report_and_refuses_existing_directory(case, tmp_path, monkeypatch):
    directory, _, _ = case

    class Clock:
        @staticmethod
        def now(tz):
            return NOW

    monkeypatch.setattr(
        evidence,
        "datetime",
        type("Clock", (), {"now": Clock.now, "fromisoformat": datetime.fromisoformat}),
    )
    target = tmp_path / "new-case"
    args = {
        "incident_id": "drill-1",
        "app_commit": "c" * 40,
        "incident_at": "2026-10-04T12:30:00Z",
        "exercise_kind": "synthetic",
    }
    evidence.initialise(directory / "restore-report.json", target, **args)
    assert (target / "restore-report.json").read_bytes() == (
        directory / "restore-report.json"
    ).read_bytes()
    assert evidence.evaluate(target, now=NOW)["status"] == "incomplete"
    with pytest.raises(evidence.EvidenceError):
        evidence.initialise(directory / "restore-report.json", target, **args)


def test_cli_incomplete_exit_and_private_failure(case, monkeypatch, capsys):
    from scripts import recovery_evidence as cli

    directory, _, _ = case
    monkeypatch.setattr(cli.os, "umask", lambda _mask: None)
    monkeypatch.setattr(cli, "evaluate", lambda path: evidence.evaluate(path, now=NOW))
    monkeypatch.setattr(
        "sys.argv", ["recovery_evidence", "evaluate", "--case-directory", str(directory)]
    )
    with pytest.raises(SystemExit) as result:
        cli.main()
    assert result.value.code == 2
    output = json.loads(capsys.readouterr().out)
    assert output["status"] == "incomplete" and output["automatic_release"] is False
    (directory / "case.json").write_text('{"secret": "synthetic-private-secret"}')
    with pytest.raises(SystemExit) as error:
        cli.main()
    assert str(error.value) == "Recovery evidence invalid; case not accepted"
    assert "synthetic-private-secret" not in str(error.value) + capsys.readouterr().out
