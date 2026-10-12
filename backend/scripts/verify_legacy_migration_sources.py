"""Offline recovery proof for manual SQL history. Never run recovered SQL."""

import argparse
import hashlib
import json
from pathlib import Path
import re


class MigrationSourceError(ValueError):
    pass


def verify_sources(history: list, directory: Path) -> dict:
    if not isinstance(history, list) or not history or not directory.is_dir():
        raise MigrationSourceError("Missing migration history or source directory")
    root = directory.resolve()
    seen = set()
    results = []
    for record in history:
        if not isinstance(record, dict):
            raise MigrationSourceError("Invalid migration record")
        name = record.get("filename")
        expected = record.get("checksum")
        if (not isinstance(name, str)
                or not re.fullmatch(r"[0-9]+[a-z]*_[a-z0-9_]+\.sql", name)
                or name in seen):
            raise MigrationSourceError("Invalid or duplicate migration filename")
        if not isinstance(expected, str) or not re.fullmatch(r"[0-9a-f]{64}", expected):
            raise MigrationSourceError("Missing or invalid recorded SHA-256")
        seen.add(name)
        path = root / name
        if not path.is_file() or path.resolve().parent != root:
            raise MigrationSourceError("Missing or out-of-scope migration source")
        original = path.read_bytes()
        original.decode("utf-8")
        lf = original.replace(b"\r\n", b"\n")
        candidates = {"original_bytes": original, "LF_bytes": lf,
                      "CRLF_bytes": lf.replace(b"\n", b"\r\n")}
        reconstruction = next((label for label, content in candidates.items()
                               if hashlib.sha256(content).hexdigest() == expected), None)
        if reconstruction is None:
            raise MigrationSourceError("Applied migration checksum has no matching source bytes")
        results.append({"filename": name, "recorded_sha256": expected,
                        "source_file_sha256": hashlib.sha256(original).hexdigest(),
                        "reconstruction": reconstruction, "applied_bytes_verified": True})
    return {
        "read_only": True,
        "sql_executed": False,
        "applied_count": len(results),
        "all_applied_sources_verified": True,
        "original_byte_matches": sum(row["reconstruction"] == "original_bytes" for row in results),
        "line_ending_reconstructions": sum(row["reconstruction"] != "original_bytes" for row in results),
        "source_sql_not_in_applied_history": sorted(p.name for p in root.glob("*.sql") if p.name not in seen),
        "migrations": sorted(results, key=lambda row: row["filename"]),
        "conversion_ready": False,
        "scope": "Exact reconstruction of applied SQL bytes; no live schema or data conversion proof",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("history", type=Path)
    parser.add_argument("source_directory", type=Path)
    args = parser.parse_args()
    try:
        raw = args.history.read_bytes()
        report = verify_sources(json.loads(raw), args.source_directory)
        report["history_file_sha256"] = hashlib.sha256(raw).hexdigest()
    except (OSError, ValueError, TypeError):
        print(json.dumps({"all_applied_sources_verified": False, "sql_executed": False,
                          "error": "InvalidOrMismatchedMigrationSources"}))
        return 1
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
