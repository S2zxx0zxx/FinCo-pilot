"""Bounded, offline credential-pattern inspection; never extract or print values.

Accepts ZIP artifacts, individual text files, or a built asset directory.
Binary/OCR/provider validity and arbitrary unknown credential formats are outside
this check. A zero count is explicitly not a universal secret-free attestation.
"""

from __future__ import annotations

import argparse
import json
import sys
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.check_secret_hygiene import TOKEN_PATTERNS  # noqa: E402

MAX_MEMBER = 8 * 1024 * 1024
MAX_TOTAL = 64 * 1024 * 1024
MAX_FILES = 10000


def inspect_artifact(
    path: Path, *, max_member: int = MAX_MEMBER, max_total: int = MAX_TOTAL
) -> dict:
    report: dict = {
        "text_files": 0,
        "binary_files_excluded": 0,
        "bytes": 0,
        "findings": [],
        "errors": [],
    }

    def scan(data: bytes, index: int) -> None:
        report["bytes"] += len(data)
        if len(data) > max_member or report["bytes"] > max_total:
            report["errors"].append({"member": index, "reason": "byte limit exceeded"})
            return
        try:
            text = data.decode("utf-8")
            if "\0" in text:
                raise UnicodeError()
        except UnicodeError:
            report["binary_files_excluded"] += 1
            return
        report["text_files"] += 1
        for number, line in enumerate(text.splitlines(), 1):
            for label, pattern in TOKEN_PATTERNS:
                if pattern.search(line):
                    report["findings"].append({"member": index, "line": number, "type": label})

    try:
        if path.is_file() and zipfile.is_zipfile(path):
            with zipfile.ZipFile(path) as archive:
                members = [item for item in archive.infolist() if not item.is_dir()]
                if len(members) > MAX_FILES or sum(item.file_size for item in members) > max_total:
                    report["errors"].append({"reason": "archive inventory limit exceeded"})
                    return report
                for index, member in enumerate(members, 1):
                    if member.file_size > max_member or member.flag_bits & 1:
                        report["errors"].append(
                            {"member": index, "reason": "oversize or encrypted member"}
                        )
                        continue
                    # Never trust a member path or extract it into the workspace.
                    with archive.open(member) as stream:
                        scan(stream.read(max_member + 1), index)
        else:
            files = sorted(path.rglob("*")) if path.is_dir() else [path]
            files = [item for item in files if item.is_file()]
            if not files or len(files) > MAX_FILES:
                report["errors"].append({"reason": "missing files or inventory limit exceeded"})
                return report
            for index, item in enumerate(files, 1):
                if item.is_symlink():
                    report["errors"].append({"member": index, "reason": "symlink not inspected"})
                    continue
                with item.open("rb") as stream:
                    scan(stream.read(max_member + 1), index)
                if report["bytes"] > max_total:
                    break
    except (OSError, RuntimeError, zipfile.BadZipFile):
        # Exception text and filenames can themselves contain credentials.
        report["errors"].append({"reason": "artifact could not be fully read"})
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("paths", type=Path, nargs="+")
    args = parser.parse_args()
    reports = [inspect_artifact(path) for path in args.paths]
    print(
        json.dumps(
            {"scope": "offline six-family patterns; binary files excluded", "artifacts": reports}
        )
    )
    return int(any(report["findings"] or report["errors"] for report in reports))


if __name__ == "__main__":
    raise SystemExit(main())
