# Payment failure recovery — original roadmap 39

Base main2814b290bb4543e395d79242ee7e24d4cab1af7d, after accepted refunds38.

## Repo audit and research

Existing durable reservations preserve provider creating/uncertain/ready claims past expiry; attempted orders are never blindly redispatched, modal dismissal cannot release a dispatched quote, signed capture grants once, renewal recovery/cancellation/refunds and retained deletion evidence already exist. Missing: owned fresh acquisition status/recheck UI, non-granting signed failed/authorized reconciliation, and browser verification callback concurrency protections. No new payment processor, SDK dependency, schema or billing policy is needed.

Primary documentation reviewed:
- https://razorpay.com/docs/payments/payments/late-authorisation/ — timeout failure may later authorize. A failed snapshot does not prove no debit or terminal monetary outcome.
- https://razorpay.com/docs/payments/payment-gateway/web-integration/standard/best-practices/ — orders group attempts; query provider states and use signed webhooks when callbacks are lost.
- https://razorpay.com/docs/api/payments/fetch-payments-orders/ — server fetch of payments bound to one order.
- https://razorpay.com/docs/webhooks/payments/ — captured/failed/authorized signals.
- Installed SDK Order.payments calls GET for the specific order.

Inference/decision: do not replace or release an attempted/unknown order merely because its latest attempts are failed, the quote expired, the modal closed, or a browser request timed out. The available evidence does not prove that late collection is impossible. Existing same-order recovery remains retained; a new order after financial uncertainty needs independently reviewed provider resolution. No invented cancellation API, automatic capture/refund, refund deadline or bank-credit promise.

## Implementation and verification plan

1. Authenticated own-account GET status, no client provider/user ID targeting, no-store, rate-limited, nonproduction Test/checkout gate. Read latest retained own acquisition order only.
2. Fresh order and complete bounded per-order payments GET outside SQL, with overall timeout and existing bounded SDK client. Strict financial identity/receipt/notes/INR/amount/status/capture/refund validation; duplicate/incomplete/aggregate mismatch fail closed. Require typed order attempts to equal returned count; over100 is unresolved.
3. Finish external I/O then reread current actor/credential stamp, source immutable binding and gate/key. Preserve prior captured facts; a regressed provider view is unresolved.
4. Report ready, created, authorized, failed, captured, refund-review, expired or unresolved without claiming bank credit or granting access. Activation confirmation is retained evidence; current entitlements determine access.
5. Existing encrypted signed inbox handles failed/authorized receipts, fresh GET proves bound payment visibility. Receipts process idempotently without changing subscription, claiming founder slots, releasing quote or provider POST. A late captured failure signal remains non-granting; actual capture event uses existing activation flow.
6. Recovery card can recheck from a fresh page and after callback/close/error. No localStorage payment identifiers, raw SDK/provider error text, PII or auto SDK/payment opening. Explicit Test Mode.
7. Hold checkout fence through verification; duplicate success/failure/close callbacks cannot cancel a successful payment or start another concurrent checkout. Failure is unconfirmed, not proof of no debit.
8. Preserve existing non-granting cancellation, unknown order dispatch, finite renewal consent/recovery, refund and account-deletion behavior. No mutable failure status ledger needed; existing receipts retain transport evidence and fresh GET owns observation semantics.
9. Adversarial tests cover every state, financial type/identity/currency mismatch, incomplete/duplicate inventory, timeout/unknown dispatch, key/auth/source races, prior capture regression, own status/no-store, signed failed→authorized→captured behavior, no POST/no grant/no repeat callback.
10. Native PostgreSQL/real Redis/signed HTTP concurrent failure receipt proof and outside-SQL provider I/O; full backend/frontend and all seven exact-head CI. Guarded merge and fresh-main all-seven evidence precede final acceptance.

Production/live financial acceptance remains pending. #39 does not enable collection, guarantee a terminal failure, invent an automatic new-order retry policy, or change OmniRoute/model/runtime policy. Original next #40–45 banking/AA/FIU requires the previously deferred compliant-partner eligibility decision; do not silently implement regulated production connectivity.

The native PostgreSQL CI job includes a real disposable Redis service for authenticated checkout rate limiting. The application limiter is exercised rather than bypassed. Full backend lint/type checking includes tests.
