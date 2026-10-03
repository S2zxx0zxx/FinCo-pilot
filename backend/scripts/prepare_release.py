"""Fail-closed startup gate shared by Helm init containers and release jobs.

Migrations already hold a PostgreSQL advisory lock, so concurrent replicas
serialize safely. Provider probes use temporary acceptance data only.
"""
from __future__ import annotations

import subprocess
import sys

from app.core.config import get_settings


def main() -> int:
    try:
        settings = get_settings()
        commands = [["alembic", "upgrade", "head"]]
        if settings.is_production:
            commands.extend([
                [sys.executable, "scripts/verify_production_postgres.py"],
                [sys.executable, "scripts/rotate_data_keys.py"],
                [sys.executable, "scripts/verify_production_redis.py", "--redis-only"],
                [sys.executable, "scripts/verify_production_object_storage.py"],
            ])
        for command in commands:
            # Alembic and drivers can embed connection details in exceptions.
            # Suppress raw output, report only the safe stage name on failure.
            result = subprocess.run(command, capture_output=True, timeout=600, check=False)
            if result.returncode:
                print(f"Release prerequisite failed: {command[0] if command[0] == 'alembic' else command[1]}", file=sys.stderr)
                return 1
        print("Release schema and configured dependencies: PASS")
        return 0
    except Exception as exc:
        print(f"Release preparation failed: {type(exc).__name__}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
