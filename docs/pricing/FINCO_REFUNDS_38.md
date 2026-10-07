# Reviewed refund lifecycle — roadmap 38

Base: main d522477a9003f524e0b8944be580bcc9a688f72c, after cancellation 37.
The repo audit found a signed minimal refund inbox and nonrefunded activation/cycle
validation, but no refund dispatch, observations, retained outcome or user status.

## Official research and decisions

- https://razorpay.com/docs/api/refunds/ — full/partial refunds apply to captured payments.
- https://razorpay.com/docs/api/refunds/normal-refunds-idempotent — immutable request body and X-Refund-Idempotency header, merchant authentication, conflict handling.
- https://razorpay.com/docs/api/refunds/entity — pending, processed and failed are distinct provider states. Processing is not a promise of bank credit at an exact time.
- https://razorpay.com/docs/api/refunds/fetch-multiple-refund-payment — bounded paginated per-payment inventory.
- https://razorpay.com/docs/webhooks/refunds/ — created/processed/failed/speed_changed are reconciliation signals; the latest fresh GET determines state, not delivery order.
- Installed Razorpay Python SDK payment.refund forwards headers through post_url.

No new dependency or alternative payment processor is needed. Reuse existing SDK,
SQL user-first fences, signed encrypted inbox, retained grant records and support.
No operator eligibility policy, legal window, mandatory-rights waiver, tax reversal,
instant timing or actual customer bank credit is inferred. Those require reviewed
operator facts and real deployment/provider acceptance before collecting real money.

## Concrete contract and plan

1. Default-off nonproduction Razorpay Test gate, bound merchant account/key and INR.
2. Fresh authenticated superuser supplies local activation/cycle UUID, explicit
   strict consent, exact integer approved amount and SHA-256 of actual reviewed
   eligibility/decision evidence. Never accept an arbitrary browser provider ID.
3. Read fresh payment and complete bounded refund inventory outside SQL. Validate
   amount/currency/capture/order or invoice binding, typed cumulative refund amount,
   unique refund identities and states. Refuse malformed/incomplete inventory.
4. Lock actual payment owner, reread actor and source, inspect account deletion and
   confirm cancellation of all unresolved/ready mandates before any new dispatch.
5. Commit one immutable intent per payment BEFORE one normal-speed SDK POST with
   server-generated receipt and idempotency key. Never auto-repost unknown outcomes.
   Repeating identical operator decision reconciles GETs; changed amount/evidence
   conflicts. Additional refunds after a partial or failed dispatch require an
   explicitly reviewed provider-side action; signed observations reconcile them.
6. POST return alone is not confirmation. Fresh paginated GET inventory binds the
   server receipt and amount; signed events only authorize GET reconciliation.
7. Retain every observed provider refund (including external refunds) without PII,
   raw provider payloads, secret notes, bank references or account cascade FKs.
   Processed evidence cannot regress/disappear; failed/pending can later reconcile.
8. Partial/pending/failed refunds do not invent prorated service policy. Only the
   entire processed refund sum for the currently projected paid term revokes its
   access. Preserve immutable paid dates and distinct new paid cycles. Later exact
   paid cycle clears the projection; recovery/cancellation cannot reset it.
9. Read-only own-user status plus support review link in Pricing. State descriptions
   distinguish requested/unknown/pending/processed/failed and do not guarantee credit.
   Fresh credential stamp is revalidated after provider I/O; an operator password,
   logout epoch or privilege change prevents new dispatch.
10. Pending financial outcomes block real deletion; provider evidence participates
    in deletion fingerprints and remains after purge. Existing dispatch can resolve
    during deletion; new mutation cannot start. Worker can reconcile retained facts
    after account deletion without recreating user, subscription or entitlement.
11. Adversarial tests: strict API/auth/ownership, exact identity/type/currency,
    malicious/stale/out-of-order/refund list, one POST/replay/timeout/process death,
    partial/full/cumulative/older term, paid replay, recovery, gate/key/actor/deletion
    races, retain/purge and disabled scanner starvation.
12. Native PostgreSQL concurrency, signed HTTP inbox, no SQL during SDK, downgrade
    refusal; full backend/frontend + migration + worker/Redis + Helm + hygiene CI.
    Merge only final exact head with all seven green; verify fresh main likewise.

## Operational boundaries

This engineering milestone handles locally proven acquisition and renewal payments.
Unbound captured payments remain non-granting and retry for binding/operator review;
refunds do not reopen founder offers or delete original accounting evidence. Refund
execution does not itself cancel provider collection: confirmed cancellation is a
separate prerequisite for new dispatch where a mandate exists. Chargebacks and
unverified refunds must not be called confirmed. Live keys remain refused.

An unknown dispatch with no bound provider refund closes as `external` only when a fresh complete inventory proves the entire captured payment was processed as refunds. This permits deletion without claiming the original dispatch succeeded or issuing another POST. User status shows actual provider refunds once, excluding the superseded decision amount. Known provider-bound pending decisions still require reconciliation.
