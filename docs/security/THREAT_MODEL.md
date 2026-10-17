# Threat model and acceptance boundaries

Baseline `7736a24`, review date 2026-10-15. Assets: identities/session credentials; financial ledger and documents; provider/bank/AI credentials; payment entitlements; deletion/backup evidence; service availability.

| Trust boundary | Adversary capability | Required invariant | Evidence / remaining proof |
|---|---|---|---|
| Browser → auth/API | Edit JS, localStorage, token, route IDs, fields, headers | Signed/current identity and independent object/role checks on server | RevocableJWTStrategy, Clerk session verifier, API permission matrix; actual provider acceptance blocked |
| API → workspace/DB | Substitute account/workspace IDs, race downgrade/archive/delete | Membership and write checks survive lock waits; no foreign reads/writes | current_workspace/current_writable_workspace; native concurrency tests still required |
| Payment provider → webhook inbox | Replay, alter body/signature/amount or spoof checkout success | Raw-body authenticity, exact merchant/order and idempotent durable state | payment_webhooks and checkout suites; live merchant receipts pending |
| Auth → email/MFA/passkeys | Replay reset/OTP, stale credential, fake device response | Purpose-bound token, current credential stamp, atomic consume and user verification | auth/MFA/passkey tests; real devices/Redis acceptance pending |
| Client → uploads/parser | Malformed XML/CSV/OFX/PDF, large/expanding input | Safe parser, bounded bytes/time, inert display and no payload logs | defusedxml reviewed; import logging fixed; complete byte/CPU budgets need decision and isolated fuzzing |
| API/agents → external destinations | Choose model/bank endpoint, inject tool instructions or remote error text | No cross-tenant tool authority; exact approved action; bounded trusted egress; sanitized diagnostics | MCP approvals reviewed, error redaction fixed; SaaS/self-host egress policy remains unresolved |
| Cloudflare → origin → data services | Spoof forwarding chain, bypass edge, stale cached private data | Exact proxy trust, no private cache, origin protection and provenance | edge tests/readiness/headers; exact source/topology and staging failure proof pending |
| App → telemetry/support/AI | Include financial records/secrets in exceptions, prompts or filenames | Minimize data, purpose-bound transfer and access/retention controls | Sentry source tests; import/MCP/connection patch; runtime sampling and remaining API error review pending |
| Operator/CI → release/secrets | Compromised action/dependency, unreviewed deploy, key mismatch | Pinned build, isolated secrets, review, rollback and key continuity | lock/advisory/history checks; protection, artifact and real restore proof pending |

## Isolated acceptance set

Use two synthetic users and two workspaces, owner/editor/viewer, downgraded and archived memberships, revoked sessions and mocked bank/payment/AI endpoints. ST-01 through ST-15 from the source blueprint remain the acceptance contract. Existing local tests provide partial scenario evidence; they do not establish every route or native race. No live exploit/flood requests were sent. Native PostgreSQL, Redis contention, configured-provider OAuth, certificate/origin and backup/restore acceptance need approved disposable targets or owner-controlled staging accounts.

## Identity lifecycle

Anonymous → provider/local authentication → partial signup or MFA challenge → verified mapped local identity → active session. Logout, credential reset, provider revocation or deletion must invalidate authority. Provider outage is a retryable unavailable state; it must not authorize access or auto-link an existing financial identity using email. Never change legacy encryption keys to force readiness.
