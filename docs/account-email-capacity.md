# Shared account-email capacity

The auth update on main replaced a process counter with Redis but left an
obsolete verification test, causing CI failure. Its separate GET/INCR admission
also allowed concurrent requests to exceed eight slots; failures silently
bypassed enforcement, and old tasks could decrement replacement work after TTL.

Recovery and verification now acquire opaque leases atomically through Redis
Lua and the server clock. Saturation, invalid Redis responses and Redis failure
return the same sanitized503 for every email before account lookup. Releases
remove only their own member and remain safe after expiry or repetition.

A delayed background task must renew a still-live lease before sending.
Asynchronous account lookup/delivery is bounded to90 seconds, below the120-second
lease. Cancellation releases the slot; worker crashes expire naturally. SMTP
delivery remains asynchronous: HTTP202 means accepted, not delivered. Logs
contain neither recipients nor lease/provider exception details.

The existing CI Redis proof now launches32 concurrent admissions, requires
exactly eight leases, and exercises expiry, delayed renewal and stale/double
release against real Redis. Existing HTTP/TLS email cases retain ownership,
anti-enumeration and signup-commit checks. Unit fixtures explicitly provide
Redis responses; tests do not contact an unconfigured localhost service.

Production provider credentials and inbox delivery remain separate acceptance
gates. Logout's independently registered router and the concurrent OIDC changes
are retained by this patch; it does not certify a Clerk cutover.
