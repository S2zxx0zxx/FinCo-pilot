# Original #31: checkout and provider order creation

Audited from main47dc090d8144eb7201c73243b28baa8e6c26b4ae. Existing #4 already supplied immutable INR pricing/intro-founder offers, campaign serialization, checkout reservations, SDK loading, HMAC/captured-payment evidence and a live-key refusal. This milestone extends those paths; webhook delivery/idempotency, entitlements, renewal, cancellation/refunds and comprehensive payment lifecycle remain original #32–39.

## Research and design

- [Razorpay Orders creation](https://razorpay.com/docs/api/orders/create/): integer subunit amounts, unique receipt up to40 characters, bounded notes, order identity/status; duplicate create errors do not mean that an order does not exist.
- [Orders receipt lookup](https://razorpay.com/docs/api/orders/fetch-all/): receipt filter can contain the supplied value, so recovery requires exact receipt equality, exact notes/amount/currency and complete bounded results.
- [Standard Checkout](https://razorpay.com/docs/payments/payment-gateway/web-integration/standard/integration-steps/): server order is authoritative for signature; checkout must use the same public key as order creation. Provider order creation docs warn against reusing an order for a new payment attempt, while the state model documents attempted orders persisting until capture. We therefore never reopen an attempted/paid order or silently mint a replacement. Retrying an unattempted HTTP creation is a distinct operation.
- [Python SDK](https://github.com/razorpay/razorpay-python/blob/master/razorpay/client.py): synchronous requests and optional retry loop. Transport is explicitly bounded (5s connect/20s read), redirects disabled, SDK retries disabled; provider I/O is offloaded to the thread pool outside SQL locks.

## Durable creation protocol

Migration101 adds state, public key, receipt and dispatch time to the existing reservation. Existing financial records remain; known legacy orders become ready, unbound active legacy quotes become uncertain (not assumed absent), old receipts are reconstructed, no old provider key is guessed. Empty rollback works; rollback with dispatch/reconciliation evidence refuses.

Reservation allocation keeps the existing campaign lock and refreshes loaded rows after lock acquisition. A compare-and-set transitions unstarted to creating, with full UUID receipt35 ASCII characters and the configured public key, committed BEFORE any remote create. One concurrent caller wins; others receive409 while dispatch is recent. Crash/timeout/invalid provider replies retain uncertain state and founder holds. Recovery reads the same receipt, never repeats POST, requires exactly one exact matching remote order and durable identity consistency. Missing/duplicate/incomplete results fail closed; an empty receipt lookup does not prove remote absence. Existing ready orders are fetched and validated before reuse. Key drift blocks without querying another account. Only created/unattempted/unpaid exact orders within the original quote window can reopen. Captured/attempted/expired orders remain reconciliation items.

Cancellation/expiry only release never-dispatched quotes. Browser dismissal is not proof of remote cancellation, and an order with no current payment attempt is still payable. Started quotes remain reserved for reconciliation, including founder capacity; they do NOT become founding claims or consume paid intro eligibility without verified capture. This deliberately fails closed on abandoned/uncertain orders; automatic terminal reconciliation and release need the signed lifecycle in #32–39. No unsupported remote order-cancellation or expiry API is invented. Operators must preserve unresolved records and original keys/evidence; do not clear claim columns or manually reassign capacity as a timeout workaround.

## Verification, UI and security

All checkout endpoints require an active authenticated user, are rate limited and return no-store, including errors. Payment fields have bounded provider-ID/HMAC formats. Owned durable order lookup precedes HMAC/provider calls, HMAC uses the server's bound order ID, original key must match, provider order identity/receipt/metadata/amount and actual payment ID/entity/captured flag are checked before refreshed locked evidence persistence. No card data or secrets enter the app or logs. Paid entitlements are untouched.

Frontend uses the backend-selected public key instead of a potentially stale build variable, validates exact order/plan/interval/INR/positive integer/expiry before opening the SDK and suppresses duplicate open modals. Closing during a success callback cannot send quote cancellation. Release is claimed only on successful API confirmation; unavailable/conflicting release is shown as pending reconciliation. Existing pricing styles and business prices remain.

## Acceptance and operational gates

Focused tests include exact receipt recovery after a lost remote reply without another POST, malformed/foreign metadata/ID/amount, key drift, cross-account verification, payment-ID substitution, pending expiry and alternate-plan blocking, attempted/paid re-open refusal, privacy headers and bounded SDK transport. Populated migration preserves actual legacy evidence and refuses destructive downgrade. Native PostgreSQL founder boundary proof also races two checkout callers against a blocked synthetic provider and proves one committed dispatch with SQL locks released. Provider calls use synthetic fakes, never real money.

Live key collection remains refused. Checkout is feature-disabled by default, Test Mode only; a functioning live product additionally needs #32–39 and configured production tax/identity/support/provider facts. Actual Razorpay Test Mode account acceptance is an external evidence gate, not proven by mocks or PostgreSQL concurrency. No zero-vulnerability or real-provider-payment certification is asserted.
