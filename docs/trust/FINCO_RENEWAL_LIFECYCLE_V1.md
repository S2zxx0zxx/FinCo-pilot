# Original roadmap #35: renewal lifecycle

Audited baseline: main e0ec04722bf14f2f295ec049c583d71840a87c23,
tree 1594fc9e44c1c1cd0c1a22d2e7125d6d505502db; migration 103.

## Actual existing implementation

- Immutable acquisition quotes disclose base renewal price/interval. Founder
  INR19/49 are first-purchase offers; they are not recurring provider plans.
- Canonical configured provider plans support Pro monthly INR99, Pro annual
  INR999 and Max monthly INR349. Provisioning/validation already exists.
- Checkout uses provider Orders; finite paid access comes from the signed inbox
  and a unique first-purchase grant. No renewal mandate creation or cycle ledger
  exists. Subscription.provider_subscription_id has no existing population path.
- Current processor quarantines subscription.charged and competing purchases.
  Replaying an acquisition payment must never renew a term.
- All paid activation remains default-off, isolated non-production Test Mode.

## Primary research and engineering constraints

Razorpay requires a provider plan and finite total_count when creating a
subscription. start_at must preserve existing paid introductory/founder service.
Provider creation is not customer authorization and not captured renewal proof.
subscription.charged supplies subscription/payment identities; invoices expose
the stable subscription_id, payment_id, paid amount and billing_start/billing_end.
Historical subscription.current_start/current_end cannot stand in for the specific
paid invoice when delivery is delayed or out of order. Some subscription webhook
examples encode captured as string "1"; signed projections must not confuse
wire-format differences with current provider payment truth.

Sources:
- https://razorpay.com/docs/api/payments/subscriptions/create-subscription/
- https://razorpay.com/docs/api/payments/subscriptions/fetch-subscription-id
- https://razorpay.com/docs/webhooks/subscriptions/
- https://razorpay.com/docs/api/payments/invoices/fetch-with-id/
- https://razorpay.com/docs/webhooks/best-practices/
- https://www.postgresql.org/docs/16/explicit-locking.html

## Implemented behavior and acceptance requirements

1. Durable merchant/mode/key-bound mandate creation claim linked to actual paid
   service and canonical plan. Explicit customer-selected finite cycles; no silent
   enrollment, arbitrary lifetime claim or repeat POST after ambiguous outcome.
   The 1–120-cycle cap is an application policy, not a provider limit. An unstarted
   claim may retry a failed plan GET; a dispatched claim only reconciles provider
   inventory. Set expire_by to the scheduled first charge, avoiding the provider
   default authorization window. Proven zero-paid expiry releases the active claim.
   Fetch/validate actual provider plan outside SQL locks. Customer authorizes via
   provider subscription Checkout; browser callback never grants access.
2. Retained unique renewal invoice/payment/cycle evidence and indexed retry state.
   Personal deletion retains these minimal financial records and requires external
   cleanup proof for creating, uncertain and ready mandates, even if a provider ID
   has not yet been recovered. All mandate states enter the provider fingerprint.
   Populated downgrade refuses discarding financial or processing evidence.
3. Reconcile signed subscription.charged using fresh authenticated subscription,
   plan, invoice and payment reads outside SQL locks. Exact typed amount, INR,
   captured/nonrefunded status, merchant/key/subscription/invoice/payment binding,
   original plan and complete finite invoice period required.
4. Consistent user-first locks; inactive/deletion-pending accounts cannot renew.
   Unique ledger insert, entitlement paid-through extension and processed receipt
   commit together. Duplicate payment/invoice never extends twice. Delayed older
   invoices never regress state; missing predecessor cycles retry without giving
   unearned access. A paid future invoice is deferred until its exact start; it
   cannot create access across an unpaid gap or remove existing paid coverage.
5. Finite completed mandate can finish its last proven paid cycle. No unauthorized
   upgrade, recurring founder price, Free/Max annual mandate, provider-ID rebinding,
   unexplained period jump, blind late-payment bonus or grace/cancellation/refund
   implementation borrowed from future #36-39.
6. Default off and non-production Test Mode only. Provider failures and DB commit
   ambiguity recover from durable state; no provider/SQL/PII exception logging.
   Bound provider timeouts, scanner work and worker cleanup/budget explicitly.
7. Validate authenticated API/ownership/explicit authorization, exact provider
   requests and one POST claim, introductory launch timing, real wire formats,
   wrong amounts/IDs/plans/refunds, duplicate/distinct receipts, out-of-order/missed
   cycles, calendar/month-end/annual periods, early/delayed payment, inactive and
   deletion races, key/settings/quote changes during I/O, failed/lost commit,
   populated migration refusal, native signed HTTP/PostgreSQL concurrent renewal,
   and UI pending/consent semantics. All seven final-head CI jobs, expected-head
   merge, exact tree equality, fresh main CI and canonical acceptance required.

Acceptance evidence belongs to the reviewed PR and canonical roadmap record.
No real mandate or charge has been created. Real-money release, legal assent and
provider operational acceptance remain separately gated.
