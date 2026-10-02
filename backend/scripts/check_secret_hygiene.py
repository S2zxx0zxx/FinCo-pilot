#!/usr/bin/env python3
"""Fail-closed current-tree checks for FinCo-Pilot secret hygiene.

This is intentionally dependency-free so every CI job can run it before any
application packages or deployment credentials exist. It complements provider
and repository secret-scanning features; it is not a substitute for rotating a
credential that was already exposed.
"""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))

from app.core.secret_management import plaintext_forbidden_prod_compose_names  # noqa: E402


TOKEN_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("private key", re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----")),
    ("GitHub token", re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}\b")),
    ("AWS access key", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("Slack token", re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{20,}\b")),
    ("JWT", re.compile(r"\beyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\b")),
    ("Zoho OAuth token", re.compile(r"\b1000\.[A-Za-z0-9]{20,}\.[A-Za-z0-9]{20,}\b")),
)
SAFE_MARKERS = (
    "synthetic",
    "not-for-production",
    "example",
    "replace-with",
    "your-",
    "<secret>",
    "<token>",
    "<key>",
)


def tracked_files() -> list[Path]:
    output = subprocess.check_output(
        ["git", "-C", str(ROOT), "ls-files", "-z"],
        text=False,
    )
    return [ROOT / item.decode("utf-8") for item in output.split(b"\0") if item]


def is_forbidden_env_file(path: Path) -> bool:
    rel = path.relative_to(ROOT)
    name = rel.name
    if name == ".env":
        return True
    if name.startswith(".env.") and not name.endswith((".example", ".template")):
        return True
    return False


def scan_token_patterns(path: Path, text: str) -> list[str]:
    problems: list[str] = []
    for number, line in enumerate(text.splitlines(), start=1):
        lowered = line.lower()
        if any(marker in lowered for marker in SAFE_MARKERS):
            continue
        for label, pattern in TOKEN_PATTERNS:
            if pattern.search(line):
                problems.append(f"{path.relative_to(ROOT)}:{number}: possible {label}")
    return problems


def scan_direct_secret_environment_reads() -> list[str]:
    problems: list[str] = []
    roots = (ROOT / "backend" / "app", ROOT / "backend" / "mcp_server")
    names = plaintext_forbidden_prod_compose_names()
    for base in roots:
        for path in base.rglob("*.py"):
            text = path.read_text(encoding="utf-8")
            for name in names:
                quoted = re.escape(name)
                patterns = (
                    rf"os\.getenv\(\s*['\"]{quoted}['\"]",
                    rf"os\.environ\.get\(\s*['\"]{quoted}['\"]",
                    rf"os\.environ\[\s*['\"]{quoted}['\"]\s*\]",
                )
                if any(re.search(pattern, text) for pattern in patterns):
                    problems.append(
                        f"{path.relative_to(ROOT)}: direct OS read of {name}; "
                        "use typed settings/secret sources"
                    )
    return problems


def scan_production_compose() -> list[str]:
    path = ROOT / "docker-compose.prod.yml"
    text = path.read_text(encoding="utf-8")
    problems: list[str] = []
    for name in sorted(plaintext_forbidden_prod_compose_names()):
        if re.search(rf"^\s+{re.escape(name)}\s*:", text, flags=re.MULTILINE):
            problems.append(
                f"docker-compose.prod.yml exposes {name} through the service environment"
            )

    required_markers = (
        "CREDENTIALS_DIRECTORY: /run/secrets",
        "FINCOPILOT_SECRETS_DIR",
        "POSTGRES_PASSWORD_FILE: /run/secrets/postgres_password",
    )
    for marker in required_markers:
        if marker not in text:
            problems.append(f"docker-compose.prod.yml missing secret-delivery marker: {marker}")
    return problems


def main() -> int:
    problems: list[str] = []
    files = tracked_files()

    for path in files:
        if is_forbidden_env_file(path):
            problems.append(f"{path.relative_to(ROOT)}: deployable .env files must not be tracked")
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        problems.extend(scan_token_patterns(path, text))

    problems.extend(scan_direct_secret_environment_reads())
    problems.extend(scan_production_compose())

    if problems:
        print("Secret hygiene check FAILED:", file=sys.stderr)
        for problem in sorted(set(problems)):
            print(f" - {problem}", file=sys.stderr)
        return 1

    print(
        "Secret hygiene check passed: no tracked deployable .env, known token pattern, "
        "direct secret getenv bypass, or production Compose plaintext secret mapping found."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
