"""Operator entrypoint; all credentials are environment/private-file inputs."""

import argparse
import fcntl
from contextlib import contextmanager
import asyncio
import json
import os
from pathlib import Path

from app.services.disaster_recovery import RecoveryError, backup, expire, restore, restic_env, run


@contextmanager
def operation_lock():
    path = os.environ.get("FINCO_DR_LOCK_FILE", f"/tmp/fincopilot-dr-{os.getuid()}.lock")
    descriptor = os.open(path, os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    try:
        if os.fstat(descriptor).st_uid != os.getuid():
            raise RecoveryError("Recovery lock ownership mismatch")
        fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
        yield
    finally:
        os.close(descriptor)


def main():
    os.umask(0o077)
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("backup")
    recover = commands.add_parser("restore")
    recover.add_argument("--snapshot", required=True)
    recover.add_argument("--destination", type=Path, required=True)
    expiry = commands.add_parser("expire")
    expiry.add_argument(
        "--apply",
        action="store_true",
        help="Forget expired FinCo snapshots and prune; default is dry-run",
    )
    commands.add_parser("check")
    args = parser.parse_args()
    try:
        with operation_lock():
            execute(args)
    except Exception:
        raise SystemExit("Disaster recovery operation failed; checkpoint not accepted") from None


def execute(args):
    try:
        if args.command == "backup":
            report = asyncio.run(backup())
        elif args.command == "restore":
            target = os.environ.get("FINCO_RESTORE_DATABASE_URL")
            if not target:
                raise RecoveryError(
                    "FINCO_RESTORE_DATABASE_URL required; never pass credentials in argv"
                )
            report = asyncio.run(restore(args.snapshot, target, args.destination))
        elif args.command == "expire":
            report = expire(apply=args.apply)
        else:
            run(["restic", "check", "--read-data"], env=restic_env())
            report = {"status": "encrypted_repository_data_checked_restore_not_proven"}
        print(json.dumps(report, sort_keys=True))
    except Exception:
        # Do not print exceptions/tracebacks: OS, SQL and providers can contain
        # credentials, recipients and plaintext payload details.
        raise SystemExit("Disaster recovery operation failed; checkpoint not accepted") from None


if __name__ == "__main__":
    main()
