# FinCopilot Pricing, Founder Offer & Provider-Mapping Contract V1

Status: canonical implementation contract for roadmap item #4  
Branch: `feat/pricing-offer-engine-v1`

This document is the server-side source-of-truth contract for FinCopilot's V1 pricing and pre-release founder campaign. It deliberately separates **product plans**, **acquisition offers**, **payment-provider plans**, and **subscription entitlement state** so marketing changes cannot silently change financial authorization.

## 1. Base product pricing

The canonical product price catalog remains:

| Product | Billing interval | Price | Availability |
| --- | --- | ---: | --- |
| Free | none | ₹0 | available |
| Pro | monthly | ₹99 | available |
| Pro | annual | ₹999 | available |
| Max | monthly | ₹349 | available |
| Max | annual | — | not offered in V1 |

All monetary values are stored and compared in INR minor units (paise).

The backend `PRICE_CATALOG` is authoritative. The browser, Razorpay Dashboard, query parameters, localStorage, or marketing copy are never allowed to override the canonical product price.

## 2. Founder pre-sale campaign

Campaign code: `founder_v1`.

The founder campaign applies only to **Pro Monthly** and only to users who have never completed a paid FinCopilot purchase.

| Wave | Successful founder buyers | Introductory charge | Service period | Standard price after the introductory period |
| --- | ---: | ---: | ---: | ---: |
| Founder Wave 1 | first 5,000 unique successful buyers | ₹19 | 60 days | ₹99/month |
| Founder Wave 2 | next 20,000 unique successful buyers | ₹49 | 60 days | ₹99/month |
| Standard | after founder campaign closes | ₹99 | 60 days only for an eligible first monthly purchase | ₹99/month |

The ₹19 and ₹49 amounts are **one-time acquisition prices**, not permanent subscription prices and not separate product entitlements. Every founder buyer receives the same `PRO` entitlement once the later subscription-activation lifecycle is enabled.

## 3. Campaign close rule

Founder pricing closes when the earliest of the following occurs:

1. 25,000 founder purchases have been successfully captured;
2. the configured pre-sale end timestamp is reached;
3. an administrator explicitly closes the campaign.

No code ships with a fabricated launch or pre-sale end date. Dates are operator-controlled runtime data and must be explicitly configured before the founder campaign can become active.

## 4. Public launch and the 60-day promise

For a valid pre-release founder purchase, the promised 60-day service period begins at the configured public-launch timestamp, not the payment timestamp.

A user who buys before release therefore does not lose access days while the product is still in pre-release.

For a first **standard monthly** purchase after launch:
- Pro Monthly: ₹99 for the first 60-day service period, then ₹99/month.
- Max Monthly: ₹349 for the first 60-day service period, then ₹349/month.

Pro Annual remains ₹999 for its normal annual service period. V1 does not add an extra 60 days to an annual plan.

## 5. Introductory-benefit eligibility

A user's first successfully captured paid FinCopilot purchase consumes first-purchase eligibility.

Consequences:
- cancelling and rejoining does not create a second introductory period;
- Pro → Max does not create a second introductory period;
- using another browser/device does not create a second introductory period;
- failed, abandoned, expired, or cancelled checkout attempts do not consume eligibility;
- a refund or chargeback does not automatically restore introductory eligibility.

Refund/chargeback policy execution belongs to later billing lifecycle roadmap items. V1 records enough evidence for those later decisions without silently reopening offers.

## 6. Real scarcity, never fake scarcity

The founder counter is derived from server-owned records only.

A founder slot is **claimed only by a successfully captured payment**.

Checkout may temporarily hold a slot while the user pays. Holds:
- have a short server-controlled expiry;
- are included when deciding whether a wave still has allocatable capacity;
- are not displayed as successfully claimed purchases;
- automatically stop blocking capacity when expired.

The API exposes real `claimed`, `held`, and `available` values. Marketing UI must never invent remaining-slot counts.

## 7. Checkout price reservation

Starting checkout creates or reuses a short-lived server-side quote reservation.

The reservation freezes:
- user;
- product plan;
- billing interval;
- offer code;
- amount;
- currency;
- founder wave, if any;
- campaign version;
- service-period days;
- reservation expiry.

This prevents a user who starts checkout at ₹19 from unexpectedly being charged ₹49 because another buyer completed payment while the modal was open.

Default reservation lifetime: 10 minutes. Production may configure the lifetime within a bounded safe range.

## 8. Product plan and offer are different concepts

Example:

```text
Product entitlement: PRO

Founder Wave 1 offer:
₹19 upfront
→ 60 days of Pro from public launch
→ standard recurring price ₹99/month later
```

The database and provider integration must never create fake entitlement identifiers such as `pro_19` or `pro_49`.

## 9. Razorpay provider-plan mapping

Razorpay recurring plans represent the **base recurring catalog only**:

- FinCopilot Pro Monthly — ₹99 — monthly × 1
- FinCopilot Pro Annual — ₹999 — yearly × 1
- FinCopilot Max Monthly — ₹349 — monthly × 1

No Razorpay plan is created for:
- Free;
- Founder ₹19;
- Founder ₹49;
- Max Annual.

Founder charges are acquisition-offer amounts. They must not create permanent low-price recurring plans.

Provider Plan IDs are deployment configuration, not browser state. Test and Live IDs are separate.

## 10. Provider catalog validation

Before a provider Plan ID can be considered usable, FinCopilot validates the fetched Razorpay Plan against the internal catalog:

- plan ID matches configured mapping;
- currency = INR;
- amount equals `PRICE_CATALOG`;
- period/interval match the FinCopilot billing interval;
- notes identify product = `fincopilot`;
- notes identify catalog version = `v1`;
- notes identify the expected plan and billing interval.

Any mismatch fails closed.

Plans are never auto-created during application startup. An explicit operator provisioning command may create/reuse exact matching Test Mode plans and print the resulting IDs for secure environment configuration.

## 11. Offer stacking

V1 does not stack founder pricing with coupons, referrals, credits, or another introductory discount.

If future campaigns are added, the backend must explicitly define stacking priority and maximum discount. No browser-side coupon arithmetic is authoritative.

## 12. Founder identity

A successfully captured founder purchase creates a persistent server-owned Founding Member record:

- Wave 1 or Wave 2;
- claim timestamp;
- immutable originating checkout reservation.

The identity may later power a `Founding Member · Wave 1/2` badge or community access.

Founder recognition is not a lifetime ₹19/₹49 subscription promise.

## 13. Admin controls and auditability

Administrators can:
- schedule the campaign;
- activate it only after required timestamps are valid;
- pause it;
- resume it;
- close it.

Price and wave-capacity constants remain code-reviewed V1 contract values rather than editable dashboard numbers.

Every campaign-state mutation is audit logged with:
- actor;
- event type;
- before/after state;
- timestamp.

## 14. Tax disclosure

FinCopilot does not guess tax treatment.

Runtime tax display mode is one of:
- `unconfigured`;
- `inclusive`;
- `exclusive`.

Production paid checkout must remain fail-closed while tax display mode is `unconfigured`.

Actual GST/invoicing treatment must be aligned with the operator's legal/tax position before Live Mode.

## 15. Currency

V1 checkout and founder offers are INR-only.

No FX conversion is used to manufacture a billing price.

## 16. Test and Live separation

Test and Live Razorpay keys and Plan IDs are separate configurations.

An operator provisioning command defaults to refusing Live keys unless an explicit Live override is supplied.

**Roadmap #4 checkout is Test Mode only.** The checkout API refuses `rzp_live_*` keys while signed webhook/subscription fulfilment is not implemented. This prevents real customers being charged before durable server-to-server entitlement reconciliation exists.

No credential or provider secret is stored in source control.

## 17. Payment verification and entitlement boundary

Browser checkout success is never sufficient.

A verified checkout must:
- pass HMAC signature validation;
- fetch Razorpay order and payment server-side;
- match reservation/order/payment/user;
- match reserved amount and INR currency;
- require captured payment before consuming a founder slot;
- be idempotent.

Roadmap #4 records the successful purchase and founder claim but **does not activate Pro/Max entitlements**. Production paid-plan activation remains the responsibility of the later signed-webhook/subscription lifecycle roadmap items.

## 18. Analytics contract

Only real server-side events are counted for core funnel metrics:
- checkout reservation created;
- provider order created;
- payment captured/verified;
- founder claim created;
- reservation expired/cancelled.

No synthetic conversion or user counters are allowed.

Traffic-source/page-view analytics may be added later only with the project's privacy/retention policy; #4 does not add invasive third-party tracking.

## 19. Required edge cases

The implementation must cover:
- Wave 1 capacity boundary;
- Wave 2 capacity boundary;
- simultaneous buyers at a boundary;
- active reservation reuse;
- expired reservation release;
- failed provider order creation;
- duplicate verification callback;
- wrong user;
- wrong reservation;
- wrong amount;
- wrong currency;
- wrong provider order/payment;
- non-captured payment;
- already-used intro eligibility;
- Free checkout;
- Max Annual;
- offer stacking attempts;
- campaign paused/closed/expired.

## 20. Completion gate

Roadmap #4 is code-complete only when:

1. canonical base pricing remains single-source;
2. founder campaign contract is implemented server-side;
3. real counters and reservation locking exist;
4. founder identity is persistent;
5. provider base-plan mapping and validation exist;
6. explicit Razorpay Test catalog provisioning/verification tooling exists;
7. admin campaign controls and audit trail exist;
8. pricing API exposes real campaign state/counters;
9. pricing UI renders server values without fake scarcity;
10. automated backend/frontend tests cover the contract;
11. migration chain, PostgreSQL migration smoke, Ruff, type-check, backend tests, frontend lint/typecheck/build/tests, and Helm checks are green;
12. no paid entitlement is activated by this branch.

The later roadmap still owns signed webhooks, recurring-subscription activation, renewals, past-due/grace, cancellation and refund execution.
