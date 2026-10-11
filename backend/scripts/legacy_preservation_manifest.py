"""Verify saved all-table restore evidence and enumerate unmapped legacy fields.

Offline only: no DB connection, SQL, migration, passwords or application imports.
Passing this check proves snapshot comparison, never conversion/cutover readiness.
"""

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re


class EvidenceError(ValueError):
    pass


def _name(value) -> str:
    if not isinstance(value, str) or not value.strip() or len(value) > 256:
        raise EvidenceError("Invalid catalogue identifier")
    return value


def _counts(entries) -> dict[str, tuple[int, str]]:
    if not isinstance(entries, list) or not entries:
        raise EvidenceError("Missing table fingerprints")
    result = {}
    for entry in entries:
        if not isinstance(entry, dict):
            raise EvidenceError("Invalid fingerprint entry")
        name = _name(entry.get("table_name"))
        count = entry.get("row_count")
        if isinstance(count, bool) or not isinstance(count, (int, str)):
            raise EvidenceError("Invalid row count")
        if not re.fullmatch(r"0|[1-9][0-9]*", str(count)):
            raise EvidenceError("Invalid row count")
        digest = entry.get("row_digest")
        if not isinstance(digest, str) or not re.fullmatch(r"[0-9a-fA-F]{64}", digest):
            raise EvidenceError("Invalid SHA-256 fingerprint")
        if name in result:
            raise EvidenceError("Duplicate table fingerprints")
        result[name] = (int(count), digest.lower())
    return result


def build_manifest(evidence: dict) -> dict:
    if not isinstance(evidence, dict):
        raise EvidenceError("Invalid evidence document")
    project = _name(evidence.get("project_id"))
    source_branch = _name(evidence.get("production_branch"))
    restored_branch = _name(evidence.get("restored_branch"))
    if source_branch == restored_branch:
        raise EvidenceError("Restore comparison must use an independent branch")
    source = _counts(evidence.get("source_table_fingerprints"))
    restored = _counts(evidence.get("restored_table_fingerprints"))
    catalogue = evidence.get("tables")
    if not isinstance(catalogue, list) or not catalogue:
        raise EvidenceError("Missing source catalogue")
    columns = {}
    for table in catalogue:
        if not isinstance(table, dict):
            raise EvidenceError("Invalid catalogue table")
        name = _name(table.get("table_name"))
        if name in columns:
            raise EvidenceError("Duplicate catalogue table")
        fields = table.get("columns")
        if not isinstance(fields, list) or not fields:
            raise EvidenceError("Missing source columns")
        names = [_name(field.get("column")) for field in fields if isinstance(field, dict)]
        if len(names) != len(fields) or len(set(names)) != len(names):
            raise EvidenceError("Invalid or duplicate source columns")
        columns[name] = sorted(names)
    if set(source) != set(restored) or set(source) != set(columns):
        raise EvidenceError("Catalogue/source/restore table sets differ")
    if source != restored:
        raise EvidenceError("Source and restored row counts or fingerprints differ")

    # Explicit proposals only; no inferred workspace, identity, money or dates.
    proposals = {"users": "users", "financial_accounts": "accounts", "transactions": "transactions"}
    tables = [{
        "source_table": name,
        "source_columns_requiring_mapping": columns[name],
        "row_count": source[name][0],
        "source_sha256": source[name][1],
        "restore_matches": True,
        "disposition": "unmapped_preserve_unchanged",
        "proposed_current_table": proposals.get(name),
        "review_required": True,
    } for name in sorted(source)]
    return {
        "format_version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "evidence_date": evidence.get("verified_at"),
        "project_id": project,
        "source_branch": source_branch,
        "restored_branch": restored_branch,
        "read_only": True,
        "snapshot_restore_verified": True,
        "table_count": len(tables),
        "row_count": sum(count for count, _ in source.values()),
        "nonempty_table_count": sum(count > 0 for count, _ in source.values()),
        "source_column_count": sum(len(fields) for fields in columns.values()),
        "conversion_ready": False,
        "cutover_authorized": False,
        "scope": "Saved snapshot comparison; not live schema or converted-application acceptance",
        "blocking_contracts": [
            "Verified provider issuer/subject and existing session transition",
            "Workspace ownership and all legacy user-reference types",
            "Authoritative per-account opening/current balances and unknown representation",
            "Transaction currency, direction, dates, tombstones, duplicate and transfer semantics",
            "Credentials/encryption keys, object references, deletion holds and provider state",
            "Reviewed disposition and field mapping for every legacy table",
            "Reachable isolated native application rehearsal and rollback acceptance",
        ],
        "tables": tables,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("evidence", type=Path)
    args = parser.parse_args()
    try:
        data = args.evidence.read_bytes()
        manifest = build_manifest(json.loads(data))
        manifest["evidence_file_sha256"] = hashlib.sha256(data).hexdigest()
    except (OSError, ValueError, TypeError):
        # No raw JSON, row values, paths or parser exception context in output.
        print(json.dumps({"snapshot_restore_verified": False, "conversion_ready": False,
                          "error": "InvalidOrMismatchedPreservationEvidence"}))
        return 1
    print(json.dumps(manifest, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
