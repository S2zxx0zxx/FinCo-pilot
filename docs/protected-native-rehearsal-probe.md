# Temporary native rehearsal connectivity probe — never merge

This branch's Vercel entrypoint is a read-only diagnostic, not the FinCo-Pilot
application and not a UI preview. Do not merge its pyproject entrypoint into main.
The existing API project's Vercel Authentication protects all preview deployments
except custom domains. Never attach a custom domain to this diagnostic.

The branch-scoped sensitive FINCO_REHEARSAL_DATABASE_URL points only at existing
isolated Neon rehearsal br-snowy-hill-az6xrk9v. Explicit preview, enabled and branch
flags and an exact pinned host/database/role allowlist are required before any
driver connection. No production DATABASE_URL or shared auth/encryption secret is
modified. Other environments fail closed.

GET /internal/rehearsal-evidence opens asyncpg with verified certificate and
hostname TLS, establishes a repeatable-read READ ONLY transaction, checks the
server's transaction_read_only setting and inventories only table names, column
metadata and row counts. No identity, financial row values, credentials or raw
driver errors are exported. Table identifiers are quoted. The probe accepts no
SQL, table, connection or query inputs from HTTP. Requests and commands have
bounded timeouts and the connection is closed. Responses use no-store.

As in the existing application asyncpg runtime, provider libpq sslmode and
channel_binding query parameters are normalized away and TLS is explicit. This
probe does not prove SCRAM channel binding and reports channel_binding_verified
false. It proves native transport/metadata access only, never converted schema
compatibility, identity ownership, financial semantics or application readiness.

After capturing evidence, disable the branch-scoped rehearsal flag and delete its
temporary connection variable. No recovery branch/data is deleted. Preserve the
tested code branch and evidence for review; retain the original app on main.
