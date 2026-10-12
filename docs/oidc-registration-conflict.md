# OIDC registration conflict and callback state

An existing account may become visible between an OIDC callback's email lookup
and user creation. The previous conflict branch then assigned the incoming
issuer/subject and preferences to that account without rechecking identity or
the disabled email-link policy. Three real SQLite database regressions reproduced
wrong local/other-provider identity assignment and preference replacement.

On manager/unique-constraint creation conflicts, roll back and re-read the winning
account. Only an active account already linked to the exact issuer and subject
can proceed. Preserve its preferences and financial resources; do not seed a
second workspace/wallet/categories/rules. Reject a different identity or disabled
link policy. If explicit email linking would be allowed but its transaction raced,
return409 and require a fresh sign-in through the ordinary link-policy path.

OIDC callback state now uses atomic Redis GETDEL, matching the existing banking
OAuth store. The existing native Redis CI script verifies32 concurrent consumers
produce exactly one winner and rejects replay. Redis6.2+ is required for GETDEL;
there is no unsafe GET/DELETE fallback.

Database regressions cover manager and SQL conflicts for local, different,
matching and inactive identities. Cryptographic verification, PKCE, nonce,
workspace guards, independent logout and recovery behavior stay in their existing
paths. This is a scoped conflict/state repair, not live provider certification,
the full Clerk transition, or a universal authentication audit.
