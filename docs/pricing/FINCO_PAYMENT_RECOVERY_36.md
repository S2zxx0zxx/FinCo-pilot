# Roadmap 36 — failed payment, past-due and bounded grace

Status: implementation and local focused validation complete; exact-head CI and main acceptance pending.

## Current-main audit

Baseline a29c366c61caeda52403983056f0a0c8991ae14f contains finite acquisition (34), explicit finite Test mandates and exactly-once paid renewal cycles (35). It has no pending/halted handler, immutable grace boundary, recovery ledger or customer recovery notice. Existing Razorpay access ends at paid-through. Account deletion retains minimal financial evidence. Preserve these protections.

## Primary research and decisions

Reviewed 2026-10-06:
- https://razorpay.com/docs/webhooks/subscriptions/ — pending and halted can contain only the subscription entity; activated is not a payment receipt.
- https://razorpay.com/docs/payments/subscriptions/payment-retries/ — retries depend on payment method; business delivery/grace is a merchant policy. No application charge/retry POST in this change.
- https://razorpay.com/docs/payments/subscriptions/states/ — reactivation does not automatically charge historical unpaid invoices. Preserve gaps for reconciliation.
- https://razorpay.com/docs/api/payments/subscriptions/fetch-invoices/ — verified SDK invoice.all(subscription_id=...) enumeration; bounded pagination and strict entity ownership.

Application policy: zero additional grace by default. An explicit 0–72-hour Test setting is snapshotted once at the original contiguous invoice billing_start. This ceiling is our safety bound, not a Razorpay retry guarantee. Repeated deliveries, later halted events, configuration changes and processing delays never restart grace. Paid coverage is never shortened by failure. Status alone never grants an unlimited term. No automatic provider mutations, arbitrary webhook URLs, payment details or raw failure messages are retained/displayed.

## Execution and acceptance checklist

1. Default-off nonproduction Test recovery gate; exclude disabled receipt types before scanner batch limit.
2. Fresh bound subscription/plan and complete bounded invoice inventory outside SQL transaction, followed by user-first locked revalidation. Reject wrong merchant/key/user/plan/currency/amount/period, bool numeric values, deletion, cancellation, scheduled changes and exhausted mandates.
3. Recover only the next contiguous unpaid invoice and locally reconciled paid_count. Missing paid evidence remains retryable; provider activation alone never clears debt. An old failure is superseded only when its signed period already has locally verified captured-cycle evidence.
4. Minimal retained unique mandate/period and merchant/invoice recovery evidence; nullable bounded subscription projection; migration 105 refuses populated downgrade; account deletion retains financial evidence.
5. Pure exact-boundary authorization; no existing-paid-term loss, no replay/configuration extension. Verified captured renewal resolves matching recovery atomically and clears projection.
6. Read-only customer notice, no duplicate mandate creation during recovery; safe provider-email/support guidance.
7. Adversarial failure, replay, expiry, recovery, ownership, concurrency, migration and retention tests; native signed HTTP/PostgreSQL proof; full backend/frontend and all seven exact-head CI jobs.
8. Only after verification: expected-head merge, feature/main tree equality, all seven fresh main CI jobs, append canonical acceptance with exact counts/SHAs and limitations.

Payment.failed for an acquisition is not a mandate-wide loss-of-access instruction. Existing captured-payment validation keeps it non-granting. A pending/halted collection event is reconciled from subscription and invoice evidence, not from an arbitrary failed payment's identifier. Cancellation/refunds remain steps 37/38. No real-money/live/operational acceptance is claimed.

Local validation: recovery41 cases (including out-of-order paid/failure), wider payment/renewal/account-deletion focus158 passed, previous renewal/entitlement57 passed, frontend5 cases passed, full backend Ruff/ty, frontend lint/typecheck, whitespace and single-head105 chain pass. Native PostgreSQL and full suites run in CI; no acceptance until exact-head and fresh-main checks succeed.
