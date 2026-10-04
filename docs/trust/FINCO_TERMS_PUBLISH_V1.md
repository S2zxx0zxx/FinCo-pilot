# Original #28 — Terms publication

Version FINCO_TERMS_V1_2026_10_04; source review 4 October 2026.

## Repository audit and scope

Base main e1fd716b53c3214ac61a1af57a4452e559a122b3 contains the #27 public privacy notice but no terms route, source, public terms settings or recorded acceptance flow. Inspected signup/local/OIDC registration, pricing/catalog/founder contract, checkout capture verification and live-key refusal, effective-plan cancellation handling, workspace archive/deletion contracts, exports, support and AI approvals. Server catalog is Free ₹0, Pro Monthly ₹99, Pro Annual ₹999, Max Monthly ₹349. Founder ₹19/₹49 acquisition prices are not lifetime subscriptions; quoted introductory periods and launch dates come from the immutable server reservation. Successful capture does not activate paid entitlement. Recurring fulfilment, refund execution, mandate cancellation and durable #29/#30 deletion remain pending. Existing subscription-state interpretation does not prove a provider cancellation endpoint exists.

Build public `/terms` and `GET /api/terms`, English/Hindi selection, operator/grievance facts, commercial decision placeholders, version/date and explicit draft status. Reuse #27 response-shape conventions and public schema, not privacy publication settings or a cloned acceptance flow. No login or workspace is needed; fetch omits credentials/auth headers, rejects malformed data, and API is no-store. React renders configured text without HTML. Link login/MFA, signup, pricing, support, privacy and account menu without changing signup/payment authorization.

Twelve sections cover service/operator, eligibility/security, estimates, content/sharing, AI/tools, plans/fulfilment, renewal/cancellation/refunds, acceptable use, availability/changes, exit/records, mandatory rights and complaints/privacy. No liability cap, compulsory arbitration, exclusive invented court, blanket no-refund/indemnity, operational refund promise, financial-adviser license or service SLA is invented. Reading/registering is not evidence of accepted terms; durable versioned acceptance and material-change communication require their own implementation before a paid launch. A client-only checkbox would provide false confidence and is not added.

## Primary research and its limits

- Current Indian e-commerce rules, government-hosted reproduction: https://thc.nic.in/Central%20Governmental%20Rules/Consumer%20Protection%20%28E-Commerce%29%20Rules%2C%202020.pdf. Review entity applicability, public operator/grievance disclosure, explicit purchase agreement, applicable complaint handling and cancellation/refund rights.
- Official PIB 10 September 2026 release: https://www.pib.gov.in/PressReleasePage.aspx?PRID=2308759&lang=1&reg=48. It confirms amendments commence 1 January 2027 and describes complaint copies, NCH linkage, price-reference transparency and dark-pattern self-audit. These operational requirements are not certified completed by this document. Full amendment PDF retrieval failed; do not infer unverified detailed wording or SaaS/operator applicability from secondary summaries.
- Razorpay official refunds: https://razorpay.com/docs/payments/refunds/. Merchant eligibility, initiating a refund and provider processing state/time are separate. Availability in provider documentation does not mean FinCo-Pilot implements execution or guarantees an instant refund.
- India Code Contract Act/IT Act references were identified but full retrieval failed. This notice uses no quoted statutory text or claim that displaying terms alone establishes valid assent. Adult/competence eligibility and statutory-right preservation require operator legal review.

## Publication decisions and gate

Defaults are draft and deliberately not a binding published contract. Public identity is never inferred from private profiles. All following settings are supported by production Compose and Helm config:

| Setting | Meaning |
| --- | --- |
| TERMS_PUBLISHED | false until complete review |
| TERMS_REVIEWED_VERSION | exact version above |
| TERMS_EFFECTIVE_DATE | ISO date no later than today |
| OPERATOR_LEGAL_NAME / OPERATOR_IDENTITY_ENABLED / OPERATOR_COUNTRY_CODE | explicit actual public identity; this review is for IN |
| TERMS_CONTACT_NAME / TERMS_CONTACT_DESIGNATION | actual responsible contact and role |
| TERMS_CONTACT_EMAIL / TERMS_CONTACT_PHONE / TERMS_CONTACT_ADDRESS | real public, monitored contact channels/address |
| TERMS_PUBLIC_WEBSITE | actual HTTPS website without credentials/query/fragment |
| TERMS_REFUND_POLICY_EN / TERMS_REFUND_POLICY_HI | reviewed eligibility, request window/method and handling in each language |
| TERMS_CANCELLATION_POLICY_EN / TERMS_CANCELLATION_POLICY_HI | reviewed service-period and cancellation decisions in each language |

Publication also requires #27 privacy publication complete and `BILLING_CHECKOUT_ENABLED=false`: paid lifecycle is unfinished in this build. This deliberately blocks declaring a paid-service launch ready. Both policy languages must be reviewed for equivalent meaning. Commercial text is plain text, not HTML or connection strings; mandatory rights in the main terms still apply. Completeness does not independently verify contact ownership, legal applicability, commercial fairness or facts. Do not enable these gates using synthetic fixtures. Invalid/missing/stale publication fails startup. Public runtime status falls back to draft if required declarations disappear.

Run `python -m scripts.verify_terms_publication` from backend. Missing/disabled publication exits nonzero and reports field codes only, without personal values or secrets. Separately verify the actual deployed logged-out HTTPS deep link/API, page refresh, public links, language separation, error/retry, no cache, contact reachability and effective date. Require all seven CI jobs on the final commit and prove the same tested tree after main merge.

## Deferred live work and acceptance

User explicitly deferred #27 real facts/review/live publication until after original roadmap #60; preserve that decision. Therefore terms also remain draft while privacy publication is pending. Do not collect real money in the unfinished lifecycle. Before any paid launch: finish signed webhook/entitlement/refund/renewal/cancellation reconciliation, explicit versioned assent and any age/authority checks, pricing/tax/refund disclosures, staffed grievance procedures, current legal review (including 2027 amendment applicability), and live deployment proofs. #29/#30 still own personal/shared deletion. A terms merge is not acceptance evidence, operational compliance or production publication.
