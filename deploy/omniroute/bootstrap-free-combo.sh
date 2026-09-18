#!/usr/bin/env sh
set -eu

BASE="${OMNIROUTE_MANAGEMENT_URL:-http://127.0.0.1:20128}"
BASE="${BASE%/}"
NAME="${FINCO_COMBO_NAME:-fincopilot-free-smart}"

: "${OMNIROUTE_MANAGEMENT_KEY:?Set OMNIROUTE_MANAGEMENT_KEY to a temporary/ops OmniRoute API key with manage scope}"
: "${FINCO_FREE_MODELS:?Set FINCO_FREE_MODELS to comma-separated fully-qualified free model routes, e.g. provider/model-a,provider/model-b}"

TMP_DIR="$(mktemp -d)"
trap 'rm -rf "$TMP_DIR"' EXIT HUP INT TERM

export FINCO_COMBO_NAME="$NAME"

printf '%s\n' "Enforcing OmniRoute global strict-zero-cost + ToS-avoid guards..."
curl --fail-with-body --silent --show-error \
  -X PATCH "${BASE}/api/settings" \
  -H "Authorization: Bearer ${OMNIROUTE_MANAGEMENT_KEY}" \
  -H "Content-Type: application/json" \
  --data '{"freeAccessPolicy":"strict","excludeTosAvoid":true}' \
  > "$TMP_DIR/settings-patch.json"

curl --fail-with-body --silent --show-error \
  -H "Authorization: Bearer ${OMNIROUTE_MANAGEMENT_KEY}" \
  "${BASE}/api/settings" > "$TMP_DIR/settings.json"

python3 - "$TMP_DIR/settings.json" <<'PY'
import json
import sys

settings = json.load(open(sys.argv[1], encoding="utf-8"))
errors = []
if settings.get("freeAccessPolicy") != "strict":
    errors.append(f"freeAccessPolicy={settings.get('freeAccessPolicy')!r}")
if settings.get("excludeTosAvoid") is not True:
    errors.append(f"excludeTosAvoid={settings.get('excludeTosAvoid')!r}")
if errors:
    raise SystemExit(
        "ERROR: OmniRoute zero-spend settings were not persisted: " + ", ".join(errors)
    )
print("OK: global strict-zero-cost and ToS-avoid guards are active")
PY

printf '%s\n' "Validating every declared FinCo model against OmniRoute's curated free-tier catalog..."
curl --fail-with-body --silent --show-error \
  -H "Authorization: Bearer ${OMNIROUTE_MANAGEMENT_KEY}" \
  "${BASE}/api/free-tier/summary?excludeTosAvoid=1" > "$TMP_DIR/free-tier.json"

python3 - "$TMP_DIR/free-tier.json" <<'PY'
import json
import os
import sys

catalog = json.load(open(sys.argv[1], encoding="utf-8"))
entries = {
    f"{row.get('provider')}/{row.get('modelId')}": row
    for row in catalog.get("perModel", [])
    if isinstance(row, dict) and row.get("provider") and row.get("modelId")
}
models = [x.strip() for x in os.environ["FINCO_FREE_MODELS"].split(",") if x.strip()]

errors = []
for model in models:
    row = entries.get(model)
    if row is None:
        errors.append(f"{model}: absent from current curated free-tier catalog")
        continue
    if row.get("enabled") is False:
        errors.append(f"{model}: disabled by the current free-tier catalog")
    if row.get("tos") == "avoid":
        errors.append(f"{model}: ToS verdict is avoid")
    if row.get("trainsOnPrompts") is True:
        errors.append(f"{model}: provider/model may train on prompts")
    if row.get("hardStopGuaranteed") is not True:
        errors.append(f"{model}: free allowance is not documented as a hard billing stop")
    free_type = str(row.get("freeType") or "")
    if not free_type.startswith("recurring-"):
        errors.append(f"{model}: freeType={free_type!r} is not a recurring launch allowance")
    if row.get("eligibilityGate"):
        errors.append(f"{model}: requires eligibility gate {row.get('eligibilityGate')!r}")

if errors:
    print("ERROR: declared FinCo models failed the zero-spend/privacy preflight:", file=sys.stderr)
    for error in errors:
        print(f"  - {error}", file=sys.stderr)
    raise SystemExit(3)

print(f"OK: {len(models)} declared model(s) passed curated recurring/hard-stop/privacy preflight")
PY

python3 - "$TMP_DIR/payload.json" "$TMP_DIR/policy.json" <<'PY'
import json
import os
import sys

models = [x.strip() for x in os.environ["FINCO_FREE_MODELS"].split(",") if x.strip()]
if not models:
    raise SystemExit("FINCO_FREE_MODELS produced an empty model list")
if any("/" not in model for model in models):
    bad = [m for m in models if "/" not in m]
    raise SystemExit(
        "Every FinCo free model must be fully qualified as provider/model. "
        f"Invalid: {bad}"
    )
if len(models) != len(set(models)):
    raise SystemExit("FINCO_FREE_MODELS contains duplicates")

providers = sorted({model.split("/", 1)[0] for model in models})
name = os.environ["FINCO_COMBO_NAME"]
max_attempts = min(12, max(3, len(models) * 2))

payload = {
    "name": name,
    "displayName": "FinCo Free Smart",
    "description": "FinCo-Pilot zero-spend production routing boundary. Approved free targets only.",
    "models": models,
    "strategy": "auto",
    "allowedProviders": providers,
    "config": {
        "candidatePool": providers,
        "healthCheckEnabled": True,
        "trackMetrics": True,
        "maxGlobalAttempts": max_attempts,
    },
}

with open(sys.argv[1], "w", encoding="utf-8") as fh:
    json.dump(payload, fh, separators=(",", ":"))
with open(sys.argv[2], "w", encoding="utf-8") as fh:
    json.dump(
        {"name": name, "models": models, "providers": providers},
        fh,
        separators=(",", ":"),
    )
PY

curl --fail-with-body --silent --show-error \
  -H "Authorization: Bearer ${OMNIROUTE_MANAGEMENT_KEY}" \
  "${BASE}/api/combos?limit=200&offset=0" > "$TMP_DIR/combos.json"

if python3 - "$TMP_DIR/combos.json" "$TMP_DIR/policy.json" <<'PY'
import json
import sys

combos = json.load(open(sys.argv[1], encoding="utf-8")).get("combos", [])
policy = json.load(open(sys.argv[2], encoding="utf-8"))
match = next((c for c in combos if c.get("name") == policy["name"]), None)
if match is None:
    raise SystemExit(1)

expected_providers = set(policy["providers"])
actual_providers = set(match.get("allowedProviders") or [])
config = match.get("config") or {}
candidate_pool = set(config.get("candidatePool") or (config.get("auto") or {}).get("candidatePool") or [])

def normalized_model(step):
    if isinstance(step, str):
        return step
    if not isinstance(step, dict):
        return None
    model = step.get("model")
    provider = step.get("provider") or step.get("providerId")
    if isinstance(model, str) and isinstance(provider, str) and "/" not in model:
        return f"{provider}/{model}"
    if isinstance(model, str):
        return model
    return None

actual_models = {m for m in (normalized_model(x) for x in (match.get("models") or [])) if m}
expected_models = set(policy["models"])

errors = []
if match.get("strategy") != "auto":
    errors.append(f"strategy={match.get('strategy')!r}, expected 'auto'")
if actual_providers != expected_providers:
    errors.append(f"allowedProviders={sorted(actual_providers)}, expected {sorted(expected_providers)}")
if candidate_pool != expected_providers:
    errors.append(f"candidatePool={sorted(candidate_pool)}, expected {sorted(expected_providers)}")
if actual_models != expected_models:
    errors.append(f"models={sorted(actual_models)}, expected {sorted(expected_models)}")

if errors:
    print("ERROR: existing FinCo combo does not match the declared zero-spend policy:", file=sys.stderr)
    for error in errors:
        print(f"  - {error}", file=sys.stderr)
    print("Refusing to mutate it automatically. Review/delete it in OmniRoute, then rerun.", file=sys.stderr)
    raise SystemExit(2)

print("OK: existing fincopilot-free-smart combo exactly matches the declared provider/model boundary")
raise SystemExit(0)
PY
then
  exit 0
else
  status=$?
  if [ "$status" -ne 1 ]; then
    exit "$status"
  fi
fi

printf '%s\n' "Creating ${NAME} with only the declared provider/model targets..."
curl --fail-with-body --silent --show-error \
  -X POST "${BASE}/api/combos" \
  -H "Authorization: Bearer ${OMNIROUTE_MANAGEMENT_KEY}" \
  -H "Content-Type: application/json" \
  --data-binary "@$TMP_DIR/payload.json" > "$TMP_DIR/create-response.json"

python3 - "$TMP_DIR/create-response.json" <<'PY'
import json
import sys

payload = json.load(open(sys.argv[1], encoding="utf-8"))
name = payload.get("name")
if not name:
    raise SystemExit(f"ERROR: unexpected combo create response: {payload!r}")
print(f"OK: created OmniRoute combo {name!r}")
PY

printf '%s\n' "Re-run this script once more to verify the persisted combo boundary."
