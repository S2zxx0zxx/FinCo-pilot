"""Offline recovery case tool; validates documents, never promotes a database."""

import argparse
import json
import os
from pathlib import Path

from app.core.recovery_evidence import evaluate, initialise


def main():
    os.umask(0o077)
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    init = commands.add_parser("init")
    init.add_argument("--restore-report", type=Path, required=True)
    init.add_argument("--case-directory", type=Path, required=True)
    init.add_argument("--incident-id", required=True)
    init.add_argument("--app-commit", required=True)
    init.add_argument("--incident-at", required=True)
    init.add_argument("--exercise-kind", choices=("synthetic", "live"), required=True)
    check = commands.add_parser("evaluate")
    check.add_argument("--case-directory", type=Path, required=True)
    args = parser.parse_args()
    try:
        if args.command == "init":
            report = initialise(
                args.restore_report,
                args.case_directory,
                incident_id=args.incident_id,
                app_commit=args.app_commit,
                incident_at=args.incident_at,
                exercise_kind=args.exercise_kind,
            )
        else:
            report = evaluate(args.case_directory)
    except Exception:
        raise SystemExit("Recovery evidence invalid; case not accepted") from None
    print(json.dumps(report, sort_keys=True))
    if args.command == "evaluate" and report["status"] == "incomplete":
        raise SystemExit(2)


if __name__ == "__main__":
    main()
