# Measurement definitions and scorecard

No GSC/Bing/GA4 account data retrieved in this baseline. UNKNOWN is not zero. Establish a valid 28-day baseline before proposing growth targets.

| Metric | Definition | Baseline |
|---|---|---|
| Qualified organic signup | Completed first-party signup attributed to unpaid search, with applicable consent; deduplicated | UNKNOWN |
| Activated organic user | Organic signup completing owner-approved first meaningful action; definition pending | UNKNOWN |
| Branded clicks | GSC/Bing clicks from documented FinCo-Pilot spelling/query classification | UNKNOWN |
| Nonbrand discovery | Query/page impressions and clicks excluding agreed brand terms | UNKNOWN |
| Index coverage | Eligible submitted canonical URLs indexed/excluded/error with reason and source date | UNKNOWN |
| Signup conversion rate | Eligible signup completions / consistently defined eligible organic visits; not GSC impressions | UNKNOWN |
| AI referrals | Aggregate visits with validated referral classification; UTM/referrer caveats | UNKNOWN |
| AI citation observations | Actual cited URL for fixed query, engine/model/date/region; distinguish mentions | UNKNOWN |
| Core Web Vitals | Field p75 LCP/INP/CLS with device/window; lab data reported separately | UNKNOWN |
| Cost/requests | Calls, compute, egress and actual provider bill, not guessed expense | Initial manual calls only; bill UNKNOWN |

Proposed minimal event vocabulary: `marketing_cta_click`, `signup_started`, `signup_completed`, `activation_completed`. Existing tracking must be inventoried before installation. Parameters: fixed page ID, CTA ID, coarse approved source/medium/campaign and device class. Send only events whose consent and accuracy have been verified.

Never send transaction text, amounts/balances, bank/account/workspace identifiers, email/name, recovery/invoice tokens, full referrers or arbitrary query strings. Campaign values must use an allowlist; strip sensitive/unknown query values. Authoritative signup completion is not a button click. No cross-origin identity stitching without explicit privacy review. Store only aggregate account exports outside public Git.

Experiment only with sufficient traffic, comparable segments and defined success/guardrail metrics. Record sample sizes and uncertainty; no ranking, traffic, revenue or AI-citation guarantees.
