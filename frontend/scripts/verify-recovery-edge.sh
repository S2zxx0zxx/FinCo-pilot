#!/usr/bin/env bash
set -euo pipefail
# Only disposable CI containers/build output; never a deployment mutation.
[ "${CI:-}" = "true" ] || { echo 'Refusing edge proof outside CI' >&2; exit 1; }
python3 - <<'PY'
from pathlib import Path
text = Path('../charts/fincopilot/templates/frontend/configmap-nginx.yaml').read_text()
block = text.split('  default.conf.template: |\n', 1)[1]
Path('/tmp/finco-helm-nginx.template').write_text('\n'.join(line[4:] for line in block.splitlines()) + '\n')
PY
cleanup() {
  docker rm -f finco-recovery-edge-ci >/dev/null 2>&1 || true
  if [ -f dist/index.html.recovery-ci ]; then mv dist/index.html.recovery-ci dist/index.html; fi
}
trap cleanup EXIT
for template in "$PWD/default.conf.template" /tmp/finco-helm-nginx.template; do
  docker run --rm -d --name finco-recovery-edge-ci \
    -p 127.0.0.1:18080:8080 \
    -e BACKEND_URL=http://127.0.0.1:8000 -e NGINX_RESOLVER=127.0.0.11 \
    -v "$PWD/dist:/usr/share/nginx/html:ro" \
    -v "$template:/etc/nginx/templates/default.conf.template:ro" \
    nginxinc/nginx-unprivileged:alpine >/dev/null
  ready=false
  for _ in $(seq 1 15); do
    if curl -fsS http://127.0.0.1:18080/ >/dev/null; then ready=true; break; fi
    sleep 1
  done
  if [ "$ready" != true ]; then docker logs finco-recovery-edge-ci; exit 1; fi
  for route in reset-password verify-email; do
    curl -fsS -D /tmp/finco-edge-headers -o /tmp/finco-edge-body \
      "http://127.0.0.1:18080/$route?token=synthetic-recovery-query-marker"
    grep -qi '^Cache-Control: no-store' /tmp/finco-edge-headers
    grep -qi '^Referrer-Policy: no-referrer' /tmp/finco-edge-headers
    grep -q 'FinCo-Pilot' /tmp/finco-edge-body
  done
  mv dist/index.html dist/index.html.recovery-ci
  code=$(curl -sS -D /tmp/finco-edge-headers -o /dev/null -w '%{http_code}' \
    'http://127.0.0.1:18080/reset-password?token=synthetic-recovery-query-marker')
  [ "$code" = '404' ]
  grep -qi '^Cache-Control: no-store' /tmp/finco-edge-headers
  mv dist/index.html.recovery-ci dist/index.html
  docker logs finco-recovery-edge-ci >/tmp/finco-edge-logs 2>&1
  if grep -q 'synthetic-recovery-query-marker' /tmp/finco-edge-logs; then
    echo 'Recovery query leaked into edge logs' >&2; exit 1
  fi
  docker rm -f finco-recovery-edge-ci >/dev/null
  echo 'PASS: real Nginx recovery success/error responses preserve headers and redact query tokens'
done
