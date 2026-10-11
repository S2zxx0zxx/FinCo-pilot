# Roadmap #51 — external MCP HTTPS acceptance

Status: engineering candidate; live HTTPS/client acceptance pending.
The production master includes #49 model connection and #50 AI QA; their live provider/runtime acceptance remains unresolved.

## Repository findings and implementation

The existing registered JWT credentials, workspace/plan authorization and
one-time application approvals are retained. No database migration or provider
account change is required. External MCP remains Advanced Agents gated.

- JSON responses support the 2026-07-28 per-request metadata transport, with
  server/discover, resultType and header/body consistency validation.
- Older Streamable HTTP clients negotiate 2025-03-26, 2025-06-18 or 2025-11-25.
  Initialized/cancelled lifecycle notifications return empty 202 responses;
  ping is supported. No session identifiers or SSE subscriptions are advertised.
- The old 2024-11-05 HTTP+SSE transport is not implemented/advertised. The
  first-party simple JSON client still works with headerless requests.
- Supplied browser Origin must match the configured frontend or external MCP
  origin. Missing Origin is allowed for CLI/server clients. Arbitrary Host or
  forwarded headers cannot create a trusted origin.
- Request size is bounded at 1 MiB; malformed IDs, params, arguments and
  non-finite JSON are rejected before execution. Tools/call notifications
  cannot trigger actions. Protocol mismatch is rejected before dispatch.
- Registered credentials are rechecked on discovery and lifecycle requests.
  External tool discovery respects module/capability visibility. Dispatch
  rejects newly added tools unless explicitly read-only or proposal tools.
- HTTPS frontend fallback is same-origin /mcp, not public port 8765. Production
  Nginx and development Vite forward /mcp to the optional private MCP service.
  Helm already routes /mcp directly through its ingress/Gateway.
- Claude Code HTTP configuration explicitly specifies type=http. The snippet
  is for header-capable HTTP clients, not a claim that every Desktop/host UI
  supports custom bearer headers. There is no OAuth discovery/login flow.
- Explicit external URLs cannot contain embedded credentials/query/fragment;
  production configuration requires HTTPS. Read-only tokens remain default.

## Research sources

Migration 101 already contains the portable CAST expression on current main.
This reconciliation does not rewrite an applied historical migration.

- https://modelcontextprotocol.io/specification/2026-07-28/basic/transports/streamable-http
- https://modelcontextprotocol.io/specification/2026-07-28/basic/versioning
- https://modelcontextprotocol.io/specification/2026-07-28/server/discover
- https://modelcontextprotocol.io/specification/2026-07-28/basic/index
- https://modelcontextprotocol.io/specification/2025-11-25/basic/transports
- https://code.claude.com/docs/en/mcp

The 2026 revision removes the handshake and adds required per-request
metadata/header matching; the 2025 revisions retain initialization. Responses
use JSON; subscriptions/sampling/resources/prompts are not advertised.

## Deployment and real acceptance gate

1. Start the optional MCP service and enable agents using the existing deployment
   secret-management contract. Never expose port 8765 directly to the internet.
2. Keep the actual Cloudflare Tunnel/TLS configuration; route /mcp through the
   frontend or a dedicated private MCP origin. Configure FRONTEND_URL and, for
   an explicit endpoint, AGENTS_EXTERNAL_MCP_URL to the actual HTTPS URL.
3. Create a fresh workspace-scoped read-only token through the existing UI.
   Do not paste credentials into chat, commit them, or include them in URLs.
4. In a real header-capable MCP client, verify discovery and one authorized
   read with known non-sensitive fixture data; record client/version, endpoint,
   commit, timestamp and pass/fail without recording the token or financial data.
5. Verify unauthenticated/expired/revoked credentials and a foreign workspace
   fail. For writes, use a disposable fixture, inspect the exact app approval,
   verify one execution and replay denial. Never infer approval from client chat.
6. Preserve the separately measured CI/SQL/proxy evidence and live client
   evidence. Mocks, ASGI HTTP, or synthetic TLS alone do not complete #51.

At the fresh 2026-10-11 checkpoint, public /mcp returned HTTP 200 frontend HTML,
while API health endpoints returned 404 and the API deployment was canceled.
PR #63 excludes /mcp from the Vercel SPA fallback; this does not deploy the
private MCP service. Neither historical edge denial nor frontend HTML establishes
working application authentication. No signed-in external client or deployed
backend/MCP runtime is available here. Live acceptance remains pending.

Additional reconciliation: reject oversized chunks before buffering them, retain
patched PyJWT authentication, and quote the endpoint in generated curl snippets.
