# Research, content and measurement decisions

17 October 2026. These are bounded evidence-backed decisions, not a ranking promise or a certification of production finance journeys.

## Research basis

Fresh official sources checked:

- Google indexing controls: https://developers.google.com/search/docs/crawling-indexing/robots-meta-tag and https://developers.google.com/search/docs/essentials/technical . Crawl access and index eligibility are distinct; a robots disallow is not data protection.
- Sitemaps: https://developers.google.com/search/docs/crawling-indexing/sitemaps/build-sitemap . Root placement and self-canonical eligible URLs simplify discovery. Submission is a hint, not acceptance into the index.
- AI visibility: https://developers.google.com/search/docs/appearance/ai-features and https://developers.google.com/search/docs/fundamentals/ai-optimization-guide . Ordinary useful, accessible search content remains the foundation. No invented AI-specific ranking switch.
- OpenAI bot purposes: https://developers.openai.com/api/docs/bots . SearchBot and GPTBot controls are independent. Existing training/user restrictions are preserved; no WAF bypass or global bot allowance.
- Truthful schema: https://developers.google.com/search/docs/appearance/structured-data/sd-policies . Existing WebSite and visible BreadcrumbList are appropriate. No fake ratings, offers, organization credentials, founder identity or rich-result guarantee.
- Helpful original material: https://developers.google.com/search/docs/fundamentals/creating-helpful-content and https://developers.google.com/search/docs/essentials/spam-policies . Improve one tested import guide before scaling finance articles.

Live SERP sample: three broad searches covering CSV/QIF duplicates/UPI imports, manual-account reconciliation and FinCo-Pilot branded navigation. Country localization was not controlled; no India-specific rank, volume, difficulty or CPC is reported. Ten derived concepts are in seo-keyword-research.csv. They are research-backed concepts, not ten independently measured exact-query demand estimates.

One material finding: results include unrelated apps and repositories with similar FinCopilot/FinanceCopilot names. Those properties are not claimed as FinCo-Pilot profiles, bank partners or sameAs identities. Canonical fincopilot.app and S2zxx0zxx/FinCo-pilot are the verified identity pair.

## Original technical content delivered in PR95

The existing import tutorial now documents actual source behavior at main264a6ad, with permanent source links and a genuine review date:

- CSV/QIF/OFX/QFX/CAMT format availability, subject to deployment/configuration.
- QIF ambiguous dates and selector; no claim that additional QIF reference tags become unique UPI identifiers.
- Actual duplicate key: account + external ID + date when present; otherwise account/date/amount/type/description or original description.
- Identical legitimate payments can match fallback deduplication; changed descriptions can defeat repeat matching. No universal idempotency or concurrent-import safety promise.
- Two downloadable synthetic INR rows (1000 income minus250 expense =750 net flow). Net history is not current available balance.

The implementation and UI were reviewed, and175 synthetic account/import regressions passed. No production account, statement or financial record was accessed. Existing real-app screenshots remain explicitly synthetic. No unreviewed financial advice or new public route was added. The four-page information architecture, contextual links and truthful schema remain intact.

Content register records source, intent, review trigger and pending maintainer review without inventing an author. The draft contribution is technical explanation, not legal advice or a claim that every deployment runs current main. Human/publication acceptance remains separate.

## Privacy and analytics

Marketing has no analytics collector or finance API requests. Existing landing/lib/attribution.ts constructs an opt-in event from fixed page/action IDs and coarse referral categories; tests reject PII-bearing paths and extra payload values. This remains disconnected. No parallel GA4, pixels, cookies or event transmission was added.

Search Console finalized web aggregate and country/device reports for17Sep–14Oct returned no rows. This is not evidence of zero people or visits. Bing, sessions, signup/activation cohorts, comparable conversion rates and costs remain UNKNOWN. No CAC or uplift is calculated without valid inputs. Existing aggregate reporting/dashboard code remains available for authorized sanitized data.

AI-citation-panel.csv contains25 reproducible proposed prompts across branded/product/educational intents. All are unmeasured: no conventional SERP result is presented as an AI citation. Capture country/language/surface/model/date/exact cited URL when actually testing. No simulated mentions or citation counts.

## Publication and distribution gates

No new About/contact/legal/pricing promises are invented. Existing app policy/support pages were HTTP-observed, but truthful operator identity, processor/retention facts and support availability require owner evidence. Broader finance articles, customer stories, founder proof packs and community outreach remain blocked on factual/editorial inputs or explicit recipient authorization. No messages, purchased links, fake reviews or distribution posts were sent.

## Performance and cost

Local repeated Lighthouse covers three URLs on mobile and desktop, twice each. It uses a plain uncompressed Python static server: transfer/LCP values are diagnostic lab observations and not equivalent to Vercel's compressed delivery or field p75. Live Chromium refused the environment's proxy certificate (ERR_CERT_AUTHORITY_INVALID); certificate validation was not bypassed. PageSpeed returned429 RESOURCE_EXHAUSTED. Therefore live CWV and before/after production improvement remain unverified.

Local functional acceptance separately confirms static/no-JS content, responsive layout and zero critical axe findings. No speculative visual redesign was introduced to chase an unrepresentative score. App initial graph stays214922 gzip bytes against307200 budget. No new service, paid subscription, tracker or recurring bill was created. Actual provider bandwidth/compute/crawl spending is unknown.
