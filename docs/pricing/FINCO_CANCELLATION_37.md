# Original roadmap 37: cancellation

Baseline: main `770b6eecef562459c1ca9fba38183aac2961732b`.
Audit: finite renewal mandates and captured-cycle evidence exist; no customer
cancellation API, durable dispatch record, cancellation webhook routing or UI.
Account deletion currently requires operator cancellation receipts. Paid canceled
subscriptions already retain finite access in the capability resolver.

Primary research (2026-10-07):
- https://razorpay.com/docs/api/payments/subscriptions/cancel-subscription/
- https://razorpay.com/docs/webhooks/subscriptions/

Provider cancellation is irreversible. Immediate cancellation works without an
active cycle; cycle-end cancellation can fail before activation or in the final
cycle. Application policy: explicitly authorized immediate collection stop,
preserving locally proven paid coverage. Cancellation does not imply a refund.

Implementation and acceptance checklist:
- Default-off Test-only gate; strict explicit consent; authenticated ownership.
- User-first locks and fresh merchant/key/plan/subscription binding validation.
- Durable unique cancellation record committed before one provider cancel POST.
- All provider I/O outside SQL; ambiguous dispatch never automatically repeated.
- Fresh bound cancelled GET proof required; signed cancellation webhook recovery.
- Preserve paid term; clear unpaid grace projection without resolving unpaid debt.
- Fence renewal enrollment and recovery while cancellation is unresolved.
- Reconcile delayed captured cycles without reactivating a canceled subscription.
- Minimal retained ledger and populated migration downgrade protection; deletion
  blocks unresolved outcomes, retains confirmed evidence and operator receipts.
- Customer confirmation, safe pending/error state, no raw provider details.
- Adversarial authorization, binding, timeout, replay, concurrency and paid-boundary
  tests; native PostgreSQL signed HTTP/concurrency proof and migration checks.
- Exact-head seven CI jobs, expected-head merge/tree equality, fresh main seven
  CI jobs and canonical acceptance. No production or zero-vulnerability claim.

Status: implementation in progress; acceptance pending.
