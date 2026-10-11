#!/usr/bin/env bash
set -euo pipefail
[ "${CI:-}" = true ] || { echo 'Refusing disposable MCP edge proof outside CI' >&2; exit 1; }
proof_dir=$(mktemp -d)
cleanup() {
  docker rm -f finco-mcp-edge-ci finco-mcp-upstream-ci >/dev/null 2>&1 || true
  docker network rm finco-mcp-edge-ci >/dev/null 2>&1 || true
  rm -rf "$proof_dir"
}
trap cleanup EXIT
docker network create finco-mcp-edge-ci >/dev/null
cat > "$proof_dir/upstream.conf" <<'CONF'
server {
  listen 8765;
  access_log off;
  location = /mcp {
    default_type application/json;
    add_header Cache-Control no-store always;
    if ($http_authorization != "Bearer synthetic-ci-mcp-marker") { return 401 '{"error":"authentication required"}'; }
    if ($request_method != POST) { return 405; }
    if ($http_mcp_protocol_version != "2026-07-28") { return 400; }
    if ($http_mcp_method != "server/discover") { return 400; }
    if ($http_origin != "https://fincopilot.example") { return 403; }
    return 200 '{"jsonrpc":"2.0","id":1,"result":{"resultType":"complete"}}';
  }
}
CONF
docker run --rm -d --name finco-mcp-upstream-ci --network finco-mcp-edge-ci --network-alias mcp-server \
  -v "$proof_dir/upstream.conf:/etc/nginx/conf.d/default.conf:ro" nginxinc/nginx-unprivileged:alpine >/dev/null
docker run --rm -d --name finco-mcp-edge-ci --network finco-mcp-edge-ci \
  -p 127.0.0.1:18081:8080 -e BACKEND_URL=http://backend:8000 -e NGINX_RESOLVER=127.0.0.11 \
  -v "$PWD/dist:/usr/share/nginx/html:ro" \
  -v "$PWD/default.conf.template:/etc/nginx/templates/default.conf.template:ro" \
  nginxinc/nginx-unprivileged:alpine >/dev/null
ready=false
for _ in $(seq 1 20); do
  if curl -fsS http://127.0.0.1:18081/ >/dev/null; then ready=true; break; fi
  sleep 1
done
[ "$ready" = true ] || { docker logs finco-mcp-edge-ci; exit 1; }
code=$(curl -sS -o "$proof_dir/body" -w '%{http_code}' -X POST http://127.0.0.1:18081/mcp)
[ "$code" = 401 ]
code=$(curl -sS -D "$proof_dir/headers" -o "$proof_dir/body" -w '%{http_code}' \
  -H 'Authorization: Bearer synthetic-ci-mcp-marker' -H 'MCP-Protocol-Version: 2026-07-28' \
  -H 'Mcp-Method: server/discover' -H 'Origin: https://fincopilot.example' \
  -H 'Content-Type: application/json' -d '{"jsonrpc":"2.0","id":1,"method":"server/discover"}' \
  http://127.0.0.1:18081/mcp)
[ "$code" = 200 ]
grep -qi '^Cache-Control: no-store' "$proof_dir/headers"
grep -q '"resultType":"complete"' "$proof_dir/body"
docker logs finco-mcp-edge-ci > "$proof_dir/logs" 2>&1
if grep -q 'synthetic-ci-mcp-marker' "$proof_dir/logs"; then
  echo 'MCP credential leaked in edge logs' >&2; exit 1
fi
echo 'PASS: real Nginx MCP proxy forwards auth/origin/protocol headers, preserves denial/JSON/no-store and redacts credentials'
# This validates the actual proxy with a synthetic upstream, not public TLS or MCP auth.
