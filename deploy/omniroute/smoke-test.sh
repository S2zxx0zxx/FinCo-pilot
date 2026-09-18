#!/usr/bin/env sh
set -eu

: "${OMNIROUTE_URL:?Set OMNIROUTE_URL, e.g. https://ai.example.com/v1}"
: "${OMNIROUTE_API_KEY:?Set OMNIROUTE_API_KEY to the dedicated FinCo-Pilot key}"

MODEL="${OMNIROUTE_MODEL:-fincopilot-free-smart}"
BASE="${OMNIROUTE_URL%/}"

printf '%s\n' "== OmniRoute model catalog =="
MODELS_JSON="$(curl --fail --silent --show-error \
  -H "Authorization: Bearer ${OMNIROUTE_API_KEY}" \
  "${BASE}/models")"

# Fail before sending a chat if the dedicated production combo is not exposed.
printf '%s' "${MODELS_JSON}" | python3 -c '
import json,sys,os
payload=json.load(sys.stdin)
target=os.environ.get("OMNIROUTE_MODEL","fincopilot-free-smart")
ids={str(x.get("id")) for x in payload.get("data",[]) if isinstance(x,dict)}
if target not in ids:
    print(f"ERROR: required model/combo {target!r} is not present in /v1/models", file=sys.stderr)
    sys.exit(2)
print(f"OK: {target} is present")
'

printf '%s\n' "== Authenticated inference smoke =="
RESP="$(curl --fail --silent --show-error \
  -X POST "${BASE}/chat/completions" \
  -H "Authorization: Bearer ${OMNIROUTE_API_KEY}" \
  -H "Content-Type: application/json" \
  -d "$(python3 -c 'import json,os; print(json.dumps({"model":os.environ.get("OMNIROUTE_MODEL","fincopilot-free-smart"),"messages":[{"role":"user","content":"Reply with exactly: FINCO_OMNIROUTE_OK"}],"temperature":0,"max_tokens":32}))')")"

printf '%s' "${RESP}" | python3 -c '
import json,sys
payload=json.load(sys.stdin)
choices=payload.get("choices") or []
if not choices:
    raise SystemExit("ERROR: no choices returned")
content=((choices[0].get("message") or {}).get("content") or "").strip()
if "FINCO_OMNIROUTE_OK" not in content:
    raise SystemExit(f"ERROR: unexpected model response: {content!r}")
print("OK: real LLM request completed through OmniRoute")
'
