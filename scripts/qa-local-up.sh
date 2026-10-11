#!/usr/bin/env bash
# Bring up a truly isolated, loopback-only copy of the ORIGINAL FinCo-Pilot.
# Never connects to the Vercel deployments, remote Neon production DB, or live users.
set -euo pipefail
umask 077

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE="$ROOT/.finco-qa.env"

command -v docker >/dev/null || { echo "Docker is required." >&2; exit 1; }
docker compose version >/dev/null || { echo "Docker Compose V2 is required." >&2; exit 1; }
command -v python3 >/dev/null || { echo "Python 3 is required." >&2; exit 1; }

if [[ ! -f "$ENV_FILE" ]]; then
  python3 - "$ENV_FILE" <<'PY'
import pathlib, secrets, sys
path = pathlib.Path(sys.argv[1])
password = secrets.token_urlsafe(32)
db_password = secrets.token_urlsafe(32)
secret = secrets.token_urlsafe(48)
path.write_text(
    f"FINCO_QA_EMAIL=qa-owner@example.com\n"
    f"FINCO_QA_PASSWORD={password}\n"
    f"FINCO_QA_DB_PASSWORD={db_password}\n"
    f"FINCO_QA_SECRET_KEY={secret}\n"
)
path.chmod(0o600)
PY
fi

echo "Starting separate FinCo-Pilot QA Docker stack (localhost only)..."
docker compose --env-file "$ENV_FILE" -f "$ROOT/docker-compose.qa.yml" up -d --build

echo "Waiting for the real FastAPI backend and migrations..."
READY=0
for _attempt in $(seq 1 90); do
  if python3 - <<'PY'
from urllib.request import urlopen
try:
    with urlopen('http://127.0.0.1:3300/api/health/live', timeout=2) as r:
        assert r.status == 200
except Exception:
    raise SystemExit(1)
PY
  then
    READY=1
    break
  fi
  sleep 2
done

if [[ "$READY" != "1" ]]; then
  echo "QA backend did not start. Read: docker compose -f docker-compose.qa.yml logs backend" >&2
  exit 1
fi

# Bootstrap only the new empty QA database using the repository's existing
# first-admin endpoint. No account/password/token is printed or committed.
python3 - "$ENV_FILE" <<'PY'
import json
import pathlib
import sys
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

config = {}
for line in pathlib.Path(sys.argv[1]).read_text().splitlines():
    key, value = line.split('=', 1)
    config[key] = value

base = "http://127.0.0.1:3300"

def request(path, *, method="GET", data=None, headers=None):
    body = json.dumps(data).encode() if isinstance(data, dict) else data
    req = Request(base + path, data=body, method=method, headers=headers or {})
    with urlopen(req, timeout=12) as response:
        return json.load(response)

form = urlencode({
    "username": config["FINCO_QA_EMAIL"],
    "password": config["FINCO_QA_PASSWORD"],
}).encode()

def login():
    try:
        return request("/api/auth/login", method="POST", data=form, headers={
            "Content-Type": "application/x-www-form-urlencoded",
        })
    except HTTPError as exc:
        if exc.code == 400:
            return None
        raise

session = login()
if not session:
    status = request("/api/setup/status")
    if status.get("has_users"):
        sys.exit(
            "The isolated QA database already contains another user, but the "
            "private QA credentials no longer match. Stop: no data was reset."
        )
    if not status.get("setup_available"):
        sys.exit("QA setup is unavailable; no credentials or data were changed.")
    request("/api/setup/create-admin", method="POST", data={
        "email": config["FINCO_QA_EMAIL"],
        "password": config["FINCO_QA_PASSWORD"],
        "currency": "INR",
        "language": "en",
        "name": "QA Operator",
    }, headers={"Content-Type": "application/json"})
    session = login()

if not session or not isinstance(session.get("access_token"), str):
    sys.exit("QA session verification failed. No secrets were printed.")

headers = {"Authorization": "Bearer " + session["access_token"]}
me = request("/api/users/me", headers=headers)
workspaces = request("/api/workspaces", headers=headers)
if not me.get("id") or not isinstance(workspaces, list) or not workspaces:
    sys.exit("QA user or workspace verification failed.")

print("PASS: Original FastAPI login, user identity and workspace are operational.")
print("Open http://localhost:3300/ on THIS laptop. Login happens silently.")
print("Private QA credentials are stored only in the ignored .finco-qa.env file.")
PY
