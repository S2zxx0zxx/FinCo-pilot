"""Offline operator evidence validation. No database access or release authority."""

from __future__ import annotations

import hashlib
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, StrictBool

GATES = (
    "recovery_inventory",
    "containment",
    "keys",
    "deletion_holds",
    "payments",
    "objects",
    "redis",
    "runtime",
    "cutover_rollback",
    "operator_review",
)
MAX_BYTES = 1024 * 1024
HEX = r"^[a-f0-9]{64}$"
ID = r"^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$"


class EvidenceError(ValueError):
    """Public messages must not include file contents or secret paths."""


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class Gate(StrictModel):
    verified_at: str
    reviewer_id: str = Field(pattern=ID)
    artifact: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,127}$")
    sha256: str = Field(pattern=HEX)


class Case(StrictModel):
    format: str = Field(pattern=r"^finco-recovery-case-v1$")
    exercise_kind: str = Field(pattern=r"^(synthetic|live)$")
    incident_id: str = Field(pattern=ID)
    app_commit: str = Field(pattern=r"^[a-f0-9]{40}$")
    incident_at: str
    restore_report_sha256: str = Field(pattern=HEX)
    gates: dict[str, Gate]


class RestoreReport(StrictModel):
    format: str = Field(pattern=r"^finco-restore-report-v1$")
    status: str = Field(pattern=r"^quarantined_restore_verified$")
    snapshot_id: str = Field(pattern=HEX)
    backup_created_at: str
    restore_started_at: str
    restore_completed_at: str
    restore_elapsed_seconds: float = Field(ge=0, le=86400)
    target_identity_sha256: str = Field(pattern=HEX)
    tables: int = Field(ge=1)
    files: int = Field(ge=0)
    automatic_release: StrictBool
    release_gates: list[str]


def stamp(value: str) -> datetime:
    try:
        result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        raise EvidenceError("Invalid evidence timestamp") from None
    if result.tzinfo is None:
        raise EvidenceError("Evidence timestamps require timezone")
    return result.astimezone(timezone.utc)


def read_private(path: Path) -> bytes:
    # Evidence is small and offline; no arbitrary URLs or shell commands.
    if path.is_symlink() or any(p.is_symlink() for p in path.parents):
        raise EvidenceError("Evidence symlinks refused")
    if not path.is_file() or path.stat().st_mode & 0o077:
        raise EvidenceError("Evidence must be a private regular file")
    with path.open("rb") as stream:
        data = stream.read(MAX_BYTES + 1)
    if not data or len(data) > MAX_BYTES:
        raise EvidenceError("Evidence size invalid")
    return data


def load_report(data: bytes, now: datetime) -> RestoreReport:
    report = RestoreReport.model_validate_json(data)
    backup, start, completed = map(
        stamp, (report.backup_created_at, report.restore_started_at, report.restore_completed_at)
    )
    if report.automatic_release or not backup <= start <= completed <= now + timedelta(minutes=5):
        raise EvidenceError("Restore chronology or quarantine invalid")
    if abs((completed - start).total_seconds() - report.restore_elapsed_seconds) > 5:
        raise EvidenceError("Restore duration disagrees with timestamps")
    expected = {
        "fresh_deletion_ledger_and_legal_holds",
        "payment_provider_reconciliation",
        "isolated_object_store_population",
        "encryption_keys_and_fresh_redis",
        "operator_review_and_runtime_checks",
    }
    if set(report.release_gates) != expected or len(report.release_gates) != len(expected):
        raise EvidenceError("Restore release gates invalid")
    return report


def initialise(
    report_path: Path,
    directory: Path,
    *,
    incident_id: str,
    app_commit: str,
    incident_at: str,
    exercise_kind: str,
) -> dict:
    data = read_private(report_path)
    now = datetime.now(timezone.utc)
    report = load_report(data, now)
    incident = stamp(incident_at)
    if not stamp(report.backup_created_at) <= incident <= stamp(report.restore_started_at):
        raise EvidenceError("Incident must follow selected backup and precede restore")
    record = Case(
        format="finco-recovery-case-v1",
        exercise_kind=exercise_kind,
        incident_id=incident_id,
        app_commit=app_commit,
        incident_at=incident_at,
        restore_report_sha256=hashlib.sha256(data).hexdigest(),
        gates={},
    )
    if (
        directory.exists()
        or directory.is_symlink()
        or any(p.is_symlink() for p in directory.parents)
    ):
        raise EvidenceError("Fresh case directory required")
    directory.mkdir(mode=0o700, parents=True)
    (directory / "restore-report.json").write_bytes(data)
    (directory / "case.json").write_text(record.model_dump_json(indent=2))
    (directory / "restore-report.json").chmod(0o600)
    (directory / "case.json").chmod(0o600)
    return {"status": "incomplete", "missing_gates": list(GATES), "automatic_release": False}


def evaluate(directory: Path, *, now: datetime | None = None) -> dict:
    now = now or datetime.now(timezone.utc)
    case = Case.model_validate_json(read_private(directory / "case.json"))
    data = read_private(directory / "restore-report.json")
    if hashlib.sha256(data).hexdigest() != case.restore_report_sha256:
        raise EvidenceError("Restore report binding mismatch")
    report = load_report(data, now)
    incident, backup, completed = map(
        stamp, (case.incident_at, report.backup_created_at, report.restore_completed_at)
    )
    if not backup <= incident <= stamp(report.restore_started_at) or set(case.gates) - set(GATES):
        raise EvidenceError("Case chronology or gates invalid")
    artifacts = set()
    for gate in case.gates.values():
        checked = stamp(gate.verified_at)
        if not completed <= checked <= now + timedelta(minutes=5):
            raise EvidenceError("Gate evidence must follow restore")
        if gate.artifact in {"case.json", "restore-report.json"} or gate.artifact in artifacts:
            raise EvidenceError("Distinct gate artifacts required")
        artifacts.add(gate.artifact)
        if (
            not re.fullmatch(HEX, gate.sha256)
            or hashlib.sha256(read_private(directory / gate.artifact)).hexdigest() != gate.sha256
        ):
            raise EvidenceError("Gate artifact checksum mismatch")
    missing = [gate for gate in GATES if gate not in case.gates]
    rpo = (incident - backup).total_seconds()
    return {
        "status": "incomplete" if missing else "documented_gates_complete_not_promoted",
        "exercise_kind": case.exercise_kind,
        "missing_gates": missing,
        "snapshot_id": report.snapshot_id,
        "recovery_point_age_at_incident_seconds": rpo,
        "isolated_restore_seconds": report.restore_elapsed_seconds,
        "rpo_target_24h_met": rpo <= 86400,
        "rto_measured": False,
        "automatic_release": False,
    }
