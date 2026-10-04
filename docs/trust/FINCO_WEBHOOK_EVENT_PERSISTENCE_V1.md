# Original roadmap #33: durable webhook receipts and idempotency

Baseline main: `64dffdc8af52870cc17aac51a530212980655063` (#32 / PR45).
Fresh audit: authenticated raw-body ingress exists; no durable webhook event table,
dedupe constraint or committed acknowledgement exists. Existing credential key-ring,
privacy/retention and deletion schema inventories must be extended rather than bypassed.

## Engineering plan

- [x] Recover canonical scope and scan actual main before implementation.
- [x] Review Razorpay retry/raw-body/event-id semantics, PostgreSQL 16 conflict
  handling, official SDK/merchant integration source and cryptography/OWASP guidance.
- [ ] Add migration102 and a global minimum-financial-evidence inbox with a unique
  `(provider, mode, merchant, raw_body_sha256)` constraint and bounded metadata.
- [ ] Encrypt an allowlisted financial snapshot using purpose-separated HKDF/Fernet
  and existing credential key-ring; exclude contacts, cards, addresses and arbitrary notes.
- [ ] Authenticate first, persist with atomic conflict handling, commit before200;
  return503 on database/encryption/deadline failures, never log SQL parameters/payloads.
- [ ] Prove unchanged retries and changed/missing untrusted delivery headers cannot
  create duplicate receipts or poison another signed body; preserve merchant/mode isolation.
- [ ] Persist unsupported/malformed financial snapshots as quarantined receipts;
  never mutate reservations/subscriptions or run a consumer in this milestone.
- [ ] Extend deletion schema/payment evidence inventory and retention/secret/deploy docs.
- [ ] Test commit/rollback/ambiguous commit, tampering, privacy, key rotation, strict
  migration constraints/downgrade refusal and native PostgreSQL concurrent acceptance.
- [ ] Run UTC full final-head CI, expected-head merge, exact tree comparison, fresh
  merged-main CI and append canonical evidence before advancing to original #34.

## Contract and tradeoffs

Razorpay signs the raw body, not the event-id header. The delivery header is a
non-authoritative first-delivery hint, never a unique key, user lookup or fulfillment
key. Two valid different bodies with the same header remain distinct receipts;
changing/removing the header on the same body does not create another receipt.
There is no header-alias table to poison or grow on arbitrary substituted headers.
Raw-byte hash identity is transport deduplication, not a guarantee that two distinct
logical provider events with byte-identical bodies can be distinguished. Later
business processing must independently dedupe provider payment/subscription identities.

Mode is a configured deployment namespace, not a mode attested by body HMAC.
Test/Live secrets and merchant configuration must be isolated; provider signatures
cannot distinguish mode if an operator incorrectly shares keys. Live collection
and real-provider acceptance remain gated. New rows and duplicate confirmations
are acknowledged only after the transaction successfully commits. A lost commit
response returns503, allowing retry to find the same durable row. No in-memory
dedupe, network provider fetch or background-task acknowledgement is used.

The exact raw payload is used only for authentication/hash and is not retained.
The encrypted snapshot contains envelope facts and explicit financial entity IDs,
amounts/currency/status/period counters; it excludes email/contact/card/bank/IP,
arbitrary notes and unsigned headers. Missing or unsupported entity data is
quarantined. Unknown events are durably recorded for disposition, not falsely
declared processed. Future handlers must fetch/validate provider state and ownership;
this minimized snapshot is not a full replay archive. A fresh snapshot/body under
the same provider payment ID can remain a separate receipt; #34 must enforce its
own lifecycle idempotency and never downgrade paid state on old/out-of-order events.

Minimal provider transaction identifiers and financial snapshots are global billing
evidence governed by the existing reviewed payment/order retention and legal-hold
rules, not an unlimited permission to retain product or card/contact data. Account
and workspace deletion preserve this minimum evidence under the existing operator
retention/processor review, and schema inventory still fails closed on unknown tables.
Encrypted snapshot reads bind ciphertext to merchant/mode/body hash to reject row
swapping, use the existing credential legacy key ring for rotation, and never accept
plaintext fallback. Keep legacy credential keys until stored snapshots are resealed.

## Primary references

- https://razorpay.com/docs/webhooks/validate-test/
- https://razorpay.com/docs/webhooks/best-practices/
- https://github.com/razorpay/razorpay-woocommerce/blob/master/includes/razorpay-webhook.php
- https://www.postgresql.org/docs/16/sql-insert.html
- https://cryptography.io/en/latest/fernet/
- https://cheatsheetseries.owasp.org/Logging_Cheat_Sheet.html

Final CI/main evidence is recorded in the PR and canonical continuity, not assumed
by this implementation plan. No zero-vulnerability or real-money certification is claimed.
