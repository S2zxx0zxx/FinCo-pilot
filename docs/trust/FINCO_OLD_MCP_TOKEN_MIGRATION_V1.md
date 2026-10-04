# Old MCP token migration — roadmap #22

## Policy and threat boundary

Old bearer credentials without a distinguishable purpose and external registry scope must not silently become trusted internal runtime credentials. This release rejects ambiguous legacy tokens. It preserves registered external tokens issued before `token_use` existed when `ext=true`, a valid workspace ID and registry ID are present and all current database authorization checks pass.

| Credential | Result |
|---|---|
| New internal token with `token_use=internal` | Short-lived first-party call; existing workspace authorization applies |
| New external token with `token_use=external`, `ext=true`, workspace and registry ID | Current user, workspace, entitlement and registered credential checks apply |
| Registered old external token with `ext=true`, workspace and registry ID | Same external controls; no automatic privilege expansion |
| Old token with no explicit purpose or external registry scope | HTTP 401; explicitly recreate |
| Revoked, expired or credential-stale registry row | Access denied, including initialize and tool discovery |
| Malformed claims, dates or identities | Bounded HTTP 401 without bearer values or decoder details |

JWT issuer, audience and HS256 algorithm are pinned. Expiry, issuance, subject, audience and issuer are required; timestamps have strict integer types and bounded future issuance. External workspace and registry identifiers are mandatory. Fresh database reads prevent an existing ORM identity map from preserving stale user/token state across authorization checks. These controls do not retroactively cancel a request already authorized before a concurrent revocation.

Registered token rows and financial history are retained. No migration guesses who owns an unregistered token, assigns it to a default workspace, auto-registers it, or executes pending proposals. Password/authentication-epoch changes still invalidate external credentials through their credential stamp. Read-only grants, workspace membership, billing capabilities and per-write human approval remain enforced.

## Full-stack behavior

Creation requires a real JSON boolean for write permissions. The registry insert and signing complete before committing; signing failures roll back rather than leaving a ghost credential. Tokens appear only in the creation response and transient client state, never inventory responses or persisted bearer columns.

Inventory reports `active`, `expired`, `revoked` or `credential_changed`. The UI displays the server status, refreshes it every 30 seconds and prompts users to recreate stale credentials. Missing status is shown as “Refresh status” rather than guessing that a credential is active. Server authorization remains authoritative between UI refreshes. Workspace changes remount the panel and clear one-time credential state.

## Operator/client rollout

1. Deploy the backend token issuer and MCP verifier together. New internal tokens contain an explicit purpose; pre-release in-flight internal tokens may receive 401 and retry using freshly minted credentials. Avoid mixed issuer/verifier versions.
2. In the intended workspace, inventory existing registered credentials. Keep active registered old-format credentials when appropriate; replace ambiguous, expired or credential-stale credentials explicitly.
3. Create a replacement credential with the minimum needed permissions. Copy it into the intended client's secret configuration; do not paste it into logs, tickets or version control.
4. Verify initialization, tool listing and an authorized read in that exact workspace. For a write-enabled credential, verify a proposal requires explicit approval; read-only credentials must not apply changes.
5. Revoke the old registered credential after the replacement works. Verify revoked credentials fail initialization, discovery and tools. Unregistered historical credentials have no registry row to revoke; their ambiguous format is already rejected by this verifier.
6. Check API/client errors and reconcile uncertain financial execution before submitting a new write. Never replay financial changes automatically during migration.

No bulk deletion, token export, schema migration or signing-secret rotation is required. Secret rotation is a separate coordinated operations action when warranted. Rolling back to a permissive verifier can reopen the ambiguous-token trust boundary and is not a routine compatibility remedy.

## Validation and limits

Regression coverage exercises malformed/ambiguous JWTs through real MCP HTTP handling, registered legacy compatibility, revocation of discovery, strict write flags, transactional signing failure and lifecycle inventory. Existing tool/approval tests cover tenant boundaries and financial controls. Frontend tests verify migration guidance, expired/stale status and approval decisions. CI runs the full backend/frontend suites and real PostgreSQL/Redis checks.

There is no provisioned VPS or authorized live client/session yet. Production issuer/verifier deployment, actual historical-client replacement and live revocation/write-approval checks remain deployment acceptance gates. Synthetic tests are not evidence that real clients have migrated. This release continues the existing custom JWT bearer MCP integration; it does not claim a complete OAuth 2.1 authorization-server implementation.

## Research basis

- [MCP authorization specification (2025-11-25)](https://modelcontextprotocol.io/specification/2025-11-25/basic/authorization): validate token audiences and resource trust boundaries.
- [MCP security best practices](https://modelcontextprotocol.io/specification/draft/basic/security_best_practices): token passthrough is prohibited; credentials must not cross trust boundaries implicitly.
- [RFC 8725](https://www.rfc-editor.org/rfc/rfc8725): pin algorithms, validate issuer/audience and use mutually exclusive validation rules for different JWT kinds.

These principles informed explicit token-purpose separation and fail-closed legacy handling; external provider credentials are not forwarded to the MCP endpoint.
