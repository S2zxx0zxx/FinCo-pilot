# Intent ownership, measurement and experiment plan

## Small public architecture

The implementation prepares four static, initial-HTML pages; it does not choose or publish a production origin. The existing financial app remains a distinct protected/utility surface. Its branch app-shell noindex prevents it competing with the separately released public pages. This also excludes the app's current pricing/policy utility shell until a separately reviewed public rendering strategy is approved; this indexing effect must be reviewed before merge/release.

| Canonical path | Primary intent | Original contribution | Distinction / no cannibalization |
|---|---|---|---|
| `/` | Brand/product introduction | Existing product screens and contextual overview | Brand identity and overall value, not a duplicate import tutorial |
| `/features` | Evaluate supported workflow categories | Honest module/provider/data limits | Overview; link to the detailed task guide instead of repeating it |
| `/how-it-works` | First-session planning | Access, small manual dataset, review and verification checklist | Broad sequence; no detailed CSV field troubleshooting |
| `/guides/import-transactions` | Preview/review a file import | Synthetic CSV, correct net-flow-versus-balance example, dates/signs/duplicates/error recovery | One concrete task; no generic financial advice article |

Guide arithmetic: signed rows -25 +100 = +75 net flow. Neither row supplies an opening balance, so no current balance is inferred. This is product education, not a personalized financial recommendation.

Region: English/global accessibility. India/INR intent research is conditional on real product and market eligibility; existing synthetic INR screenshots do not prove regional bank/UPI coverage. No India keyword-volume claim or localized route deployed.

Keyword seeds and official competitor text sources are in RESEARCH_2026-10-15.md. Search demand, difficulty and conversion feasibility remain unmeasured until authorized data/research supplies them. Do not invent numerical opportunity scores; use the PDF weights only with supported inputs. Expand beyond this initial intent map only when a verified user need warrants it.

## Privacy-safe measurement implementation

`landing/lib/attribution.ts` is an offline pure event constructor with explicit consent and fixed page/action IDs. It strips raw referrers, query values and arbitrary parameters by construction. It performs **no network, cookie or storage operation** and is not wired into UI tracking before consent/vendor approval.

`scripts/growth_report.py` accepts authorized local aggregate CSV exports and emits aggregate JSON. Input paths/raw queries never appear in output. Unexpected identity/financial headers, empty exports, negative/missing counts and inconsistent cohorts are rejected. Brand classification recognizes FinCo-Pilot spelling variants; ambiguous queries and anonymized query-row omissions require review. Google and Bing remain separate sources.

Example usage, with local exports kept out of public Git:

```bash
python3 scripts/growth_report.py --start 2026-10-01 --end 2026-10-14 \
  --google /private/authorized-google-query-export.csv \
  --funnel /private/authorized-organic-cohort.csv > /private/growth-summary.json
```

Search CSV columns: `query` or `Top queries`, `clicks`, `impressions`; optional `CTR`, `position`. Funnel columns: `channel,visits,signups,activated`, with `organic_search` only and a consistent deduplicated cohort. Other export layouts need an explicit reviewed adapter, not silent guessing. Date interval is mandatory when supplying actual exports.

Open `docs/growth/dashboard.html` and load the sanitized report. It starts with 14 UNKNOWN metrics, uses local file input and text-only DOM rendering, and makes no network/storage calls. This is an implemented review dashboard, not a live connected business dashboard. Importing a file does not independently verify its provenance.

Windsor.ai was discovered as an optional GSC/GA4 integration. The owner reports account setup; the latest tool inventory still exposed no authenticated Windsor operations and directory metadata returned not installed. Keep access UNKNOWN/BLOCKED until a successful authorized source/property read. Do not repeat the install prompt or claim absence of the underlying GSC/GA4 accounts. Do not assume a paid Windsor plan is required or activate one.

## AI citation prompt panel

Use fixed questions: what is FinCo-Pilot; how to import transactions into FinCo-Pilot; budgeting tools without a bank link; how to map dates/amounts in a CSV import; why transaction history differs from balance; what inputs a spending estimate needs. Preserve neutral wording and query order across runs.

Each observation needs engine, visible model/version if available, date/time, region, exact query, brand mention, actual cited URL, answer excerpt within copyright limits and method. Mark unavailable fields UNKNOWN. A public web retrieval is not a ChatGPT/Bing AI citation-panel result. Do not infer citations from crawler access, or confuse citations with referral visits. No verified AI citation observation has been collected in this run.

## Conditional indexing notification

IndexNow is deferred until the final public origin and eligible URLs are live. Before implementation/activation: review current official protocol, verify host/key-file control, submit only changed canonical eligible public URLs, cap calls to one bounded release batch, and never submit auth/private/token URLs. Do not use daily repeated submissions as a ranking tactic or claim Google support. A sitemap and submission remain discovery hints, not indexing guarantees.

## Experiment ready for later measurement

Hypothesis: task-oriented navigation to the import guide helps qualified visitors understand the manual-first workflow before signup. Candidate change: one approved CTA label/location on the feature page. Primary metric: consent-eligible completed organic signups; guardrails: errors, access/privacy, mobile usability and activation. Do not change auth/billing or count CTA clicks as successful signup.

Begin only after a stable baseline, authoritative event completion and sufficient samples. Record assignment, sample size, reporting lag and uncertainty. If using sequential periods, explicitly state that seasonality/releases prevent a clean causal conclusion. There is no current experiment result or uplift claim.

## Cadence and reports

Daily technical safety + source changes; weekly query/page/indexing and intent review when data exists; monthly comparable cohort/outcome and resource review; quarterly claim/localization review. Preserve actual observation dates and source lag. Use existing deduplicated monitoring, not a new broad crawler. Detailed operating limits remain in OPERATIONS.md.
