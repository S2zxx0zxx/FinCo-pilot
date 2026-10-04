# Original roadmap #32: signed payment webhook

Update from original #33: durable receipts now provide the authenticated route
with commit-before-200 acknowledgement. The 503-only behavior below describes
this original #32 milestone; see FINCO_WEBHOOK_EVENT_PERSISTENCE_V1.md for the
current ingress contract. Live collection/fulfillment remain separately gated.

Baseline: main `b22ccc33342bbab305e453fbb38d204d4ff987b8`, original #31 / PR44.
Repository audit found browser checkout capture verification, dedicated reservation
state and permission/secret inventories, but no webhook route or signing keys.
This milestone adds authenticity ingress; original #33 owns durable event storage
and idempotency, #34 activation, and #35–39 the remaining payment lifecycle.

## Implementation and verification checklist

- [x] Inventory existing checkout, application middleware, secrets and deployment configuration.
- [x] Research provider raw-body signatures, old-key retries, duplicate delivery and acknowledgements.
- [x] Add disabled-by-default POST `/api/webhooks/razorpay` with explicit cryptographic dependency.
- [x] Bound streamed bodies to 256 KiB and a two-second read deadline; reject compression and ambiguous headers.
- [x] Verify SHA256 HMAC over exact received bytes using constant-time comparisons before JSON parsing.
- [x] Reject duplicate JSON keys, nonfinite constants, invalid UTF-8 and nesting beyond 32 levels.
- [x] Bind authenticated envelope to configured merchant account; never mutate billing in this boundary.
- [x] Register independent current/previous secrets and bounded expiry across deployment surfaces.
- [ ] Record final local and CI evidence before merging, then verify the merged main commit.

## Acceptance contract and operational gates

Disabled ingress returns 503. Enabled ingress rejects invalid signatures with 401;
malformed envelopes/ambiguous headers with 400; oversized bodies with 413;
unsupported media/compression with 415; read timeout with 408.
**A valid event also returns 503 until #33 provides a committed durable handoff.**
There is no background-task acceptance, provider API call, entitlement change or
payment success response. Every response is non-cacheable and contains no payload,
signature or signing secret. Browser JWT is neither necessary nor sufficient.

Do not register this release as an operational live webhook. Razorpay retries
non-2xx responses with exponential backoff for 24 hours, then disables delivery;
responses taking over five seconds may be redelivered. #33 must commit event
storage before acknowledging with 2xx. Live checkout remains independently closed.
Synthetic engineering proofs cannot certify a real provider account or deployment.

## Configuration and rotation

Set `RAZORPAY_WEBHOOK_ENABLED=true`, exact `RAZORPAY_WEBHOOK_ACCOUNT_ID=acc_...`
and a dedicated randomly generated `RAZORPAY_WEBHOOK_SECRET` of 32–256 printable
ASCII characters without whitespace. Never reuse `RAZORPAY_KEY_SECRET` or keys
between Test/Live endpoints. Environment files are for development; production
Compose mounts `razorpay_webhook_secret` and optional
`razorpay_webhook_previous_secret` from its existing read-only secret directory.
Helm production uses `global.existingSecret` with corresponding uppercase keys.
Shared Settings consumers must receive the same configuration and secret files.

For rotation, retain the outgoing key as previous and set
`RAZORPAY_WEBHOOK_PREVIOUS_SECRET_EXPIRES_AT` to an explicit Unix timestamp covering
the provider retry window plus operational margin. Configuration refuses an expiry
over 48 hours in the future. The request checks expiry on every delivery; an expired
previous key is never accepted. Remove previous key and reset expiry to zero after
the overlap, deploy consistently, and confirm provider delivery evidence. An expired
previous key can remain in configuration temporarily without preventing startup.
Secret source loaders may strip file newlines; use canonical whitespace-free keys.

The `x-razorpay-event-id` header is delivery metadata, **not authenticated by body
HMAC**. #33 must scope deduplication to merchant/provider and bind event IDs to body
hashes; header substitution must not poison the ledger. A valid signature is not
replay protection. Delivery order and `created_at` are not a freshness guarantee;
old legitimate retries remain valid. Paid-state decisions need persisted events
and reconciliation, not the webhook snapshot alone. Rejecting an unsupported
future event with 2xx is forbidden until its durable disposition is defined.

Use HTTPS/TLS and ingress request-size/time limits in deployment. IP allowlists
may supplement authentication but cannot replace HMAC. This route intentionally
avoids per-user/IP application quotas that could suppress shared provider traffic;
edge capacity and flood controls need real deployment acceptance. No zero-vulnerability
claim is made.

## Research references

- [Razorpay signature validation and retries after secret rotation](https://razorpay.com/docs/webhooks/validate-test/)
- [Razorpay delivery, timeout and retry contract](https://razorpay.com/docs/webhooks/best-practices/)
- [Payment event envelopes and snapshots](https://razorpay.com/docs/webhooks/payments/)
- [Official open-source Python signature implementation](https://github.com/razorpay/razorpay-python/blob/master/razorpay/utility/utility.py)
- [SDK discussion of body encoding/signature pitfalls](https://github.com/razorpay/razorpay-python/issues/121)
- [OWASP REST input, content-type and request-size guidance](https://cheatsheetseries.owasp.org/cheatsheets/REST_Security_Cheat_Sheet.html)

Standard-library HMAC avoids a new cryptographic dependency; tests cross-check the
installed provider SDK. Durable persistence and deduplication cannot be replaced
by a local-memory cache or a guessed third-party abstraction.

Focused acceptance covers 43 webhook cases and all executable statements in the
new ingress module; coverage is an execution measure, not a security guarantee.
An independent native Uvicorn HTTP rehearsal also verified genuine chunked signed
delivery (503/no-store), forged signature (401), and unfinished streaming upload
(408 within the read deadline) against the full application's middleware with
startup lifespan disabled. No external provider or database was involved.
Final full-suite CI and merged-main evidence belongs in the PR and canonical
continuity record, so this version does not predeclare those outcomes.

The final primary-source review also confirmed documented multi-segment event
names such as `payment.downtime.started`; envelope validation therefore bounds
the event name without incorrectly assuming exactly one period. Subscription and
refund envelopes are authenticatable here without activating their later lifecycle.
