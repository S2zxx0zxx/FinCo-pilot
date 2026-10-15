# IndexNow and comparable-period reporting

15 October 2026. Source implementation only; no live notification, tracking collector or actual analytics import was performed.

## Bounded IndexNow notifier

`scripts/growth_indexnow.py` implements an optional manual release operation. Current official protocol references: https://www.indexnow.org/documentation and https://www.indexnow.org/faq (checked 15 October 2026). The notifier uses the global endpoint, root text key verification and a single JSON POST. A 200 means receipt; 202 means receipt with key validation pending. Neither proves indexing. Review an existing provider integration first to avoid duplicate notifications.

- Default dry-run is entirely offline. It validates one explicit owned HTTPS origin, key syntax and one to four distinct approved public paths. Output omits the key/key-file URL.
- The key comes only from `FINCO_INDEXNOW_KEY`; no generated production key or key file is committed.
- Actual submission requires both `--submit` and `--release-approved`. Do not use these flags until the exact public release and indexing policy are approved and verified.
- Before the single POST, verify the root key file, Bing's current robots permission and each page's HTTP200/HTML, exact canonical, one initial H1 and explicit nonexcluded indexing metadata. Redirects, noindex and incorrect key/content fail closed.
- Maximum seven requests for four pages: key + robots + four pages + one notification. No retry, scheduling, daily resubmission or arbitrary URL/endpoint input. The implemented subset only supports added/updated indexable public pages, not removed/private/token URLs.
- A failed check/submission stops the run. CLI errors omit raw response bodies, key locations and exception details. Dry-run/testing uses synthetic keys only.

Offline example (synthetic key, no DNS, file installation or submission):

```bash
FINCO_INDEXNOW_KEY=synthetic-test-key-1234 python3 scripts/growth_indexnow.py \
  --origin https://discover.fincopilot.app --path /features
```

The example hostname remains a fixture. Do not interpret it as a live approved marketing host. Keep the optional notifier disconnected until the owner reviews the public-origin release. No Google support or ranking improvement is claimed.

## Comparable outcome reporting

`growth_report.py` retains its aggregate-only Google/Bing/cohort importer and adds an optional local sanitized previous report. Counts remain exact safe integers; missing metrics stay null/UNKNOWN. The report adapter rejects identity/financial columns and inconsistent cohorts. Original query rows are not emitted.

```bash
python3 scripts/growth_report.py --start 2026-10-01 --end 2026-10-14 \
  --google /private/authorized-current-google.csv \
  --funnel /private/authorized-current-cohort.csv \
  --previous /private/sanitized-previous-report.json \
  --comparable-cohorts > /private/sanitized-current-report.json
```

`--comparable-cohorts` is an operator declaration that consent, source definitions, filters, attribution and deduplicated cohorts are comparable. The software cannot verify that declaration. Without it, or for overlapping/out-of-order/unequal-duration windows, no deltas/uplift are emitted. Use matched windows for count comparisons; full calendar months with different lengths are not compared as if equivalent. Real source lag and release changes still need editorial interpretation.

For eligible known values: absolute differences, relative changes and rate differences in **percentage points** are separate. A zero previous value has no defined relative percentage change. A missing value remains unknown. Changes describe the data; they do not establish causal uplift or experiment success.

The dashboard shows descriptive comparison values only when supplied by a valid sanitized report; it rejects inconsistent zero-baseline/delta values and keeps all rendering text-only, local and without storage/network. It does not verify provenance or turn an imported file into live connected analytics.

## Monthly operating report

Use these sections with actual evidence; do not fill placeholders with guessed numbers:

1. Exact reporting windows, data lag, source/property and consent/cohort changes (private account identifiers stay outside public Git).
2. Google and Bing exported-query totals separately; branded/nonbrand limits and omitted-query caveats.
3. Organic visits, completed signup/activation cohorts and descriptive matched-window changes, with unknowns explicit.
4. Technical source/preview/live status, deployed SHA, eligible pages, indexing observations and current regressions.
5. Actual measured resource usage/cost and report period. CI runs and fixed request ceilings are not an invoice. Missing provider spend remains UNKNOWN.
6. Decisions: keep/fix/defer with evidence, uncertainty and the next quarter's prioritized work. No unsupported causal claim, numerical traffic target or forecast.

The existing daily audit prompt includes weekly, monthly and quarterly review duties without another schedule. Configuration is confirmed; subsequent execution/delivery is not observed here. Publication, live property access and actual comparable outcomes remain separate acceptance gates.

## Same-origin landing namespace

After landing activation PR92, the combined artifact serves public marketing at `/welcome/`. A later approved notification for that deployment must use `--base-path /welcome` with logical paths such as `--path /features`; this generates `/welcome/features/`, not the finance shell's `/features`. Standalone marketing retains the empty base path. Both modes remain offline by default; this instruction does not enable indexing or submit any URL.
