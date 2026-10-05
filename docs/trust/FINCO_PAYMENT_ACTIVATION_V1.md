# Original roadmap #34: payment to subscription activation

Baseline main9400051f425c26d0e48b8a4e7c95ce43f165808b / migration102.
Fresh audit: browser checkout verification records purchase/founder evidence but
never grants entitlements; the durable webhook inbox has no consumer. Existing
subscription authorization only checks canceled-period expiry. Reuse Celery Beat,
original checkout key/quote/order validation, credential ring and deletion fencing.

## Implementation and acceptance plan

1. Migration103: minimal retained activation evidence with unique payment identity
   and reservation; indexed inbox retry scheduling and sanitized disposition codes.
   Populated downgrade refuses evidence loss; explicitly review deletion inventory.
2. Durable bounded Beat scanner. Only signed payment.captured/order.paid receipts
   qualify. Missing local orders/provider outage retry with capped backoff; invalid
   or unsupported events quarantine. Worker/broker crashes leave receipts recoverable.
3. Fetch current authenticated provider payment AND order outside SQL transactions.
   Validate captured/nonrefunded exact typed INR amount, fully paid order, immutable
   receipt/notes/IDs and original key. Revalidate against the locked server quote.
4. Consistently lock active user, reservation, inbox and subscription. Atomically
   finalize purchase/founder evidence, insert unique activation, grant reserved
   plan/interval/period and process receipt. Replays never extend periods or reset
   later state. First purchase only; competing purchases/existing paid state require
   review, not implicit renewal/upgrades (#35-39).
5. Honor reserved launch/start plus service days, not webhook order/current catalog.
   Razorpay grants authorize only start <= now < end. Inactive/deleted users cannot
   be resurrected. Preserve non-provider manual/fixture compatibility.
6. Activation defaults off; this milestone permits isolated non-production Test
   Mode only. Production/Test grants and Live collection stay gated pending later
   lifecycle/provider operational acceptance. No real-money certification.
7. Prove signed HTTP inbox-to-worker-to-entitlement, duplicate/different bodies,
   mismatch/refund/provider outage, future/expired terms, deletion, concurrent
   purchases, key changes, ambiguous commit, migration refusal and native PG races.
   Final-head seven-job CI, expected-head merge, exact tree, fresh main CI and
   canonical acceptance must pass before completion.

Snapshots are historical hints, not current payment truth. No provider request is
made while SQL locks are held. Contact/card/raw bodies/provider errors are excluded
from activation records/logs. Capped indexed backoff prevents an oldest unavailable
event starving later events. An external refund occurring after a GET belongs to
the later refund/reconciliation lifecycle. Standard Checkout grants finite prepaid
service; it does not invent a provider recurring subscription.

## Primary research

- https://razorpay.com/docs/api/payments/fetch-with-id/
- https://razorpay.com/docs/api/orders/fetch-with-id/
- https://razorpay.com/docs/webhooks/best-practices/
- https://razorpay.com/docs/server-integration/python/test-app/
- https://www.postgresql.org/docs/16/explicit-locking.html
- https://www.postgresql.org/docs/16/sql-insert.html

Final test/CI/main evidence belongs to the PR and canonical continuity. This plan
does not certify deployment, live money acceptance or absence of vulnerabilities.
