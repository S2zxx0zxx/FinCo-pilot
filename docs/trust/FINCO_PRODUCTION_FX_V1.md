# Roadmap #18 — production FX provider

Status: engineering implemented; local verification passed; PR CI/merge pending. Provider account,
credential provisioning, production sync and live deployment acceptance are not
claimed. This file preserves the distinction between CI evidence and live gates.

## Research and decision (2026-10-03)

Keep the existing Open Exchange Rates adapter and USD cross-rate storage contract.
This avoids changing the financial meaning or attribution of existing stored
conversions. Official Free signup currently lists hourly updates, daily historical
data and 1,000 requests/month; no card is required. Two scheduled syncs/day leave
substantial capacity for bounded historical imports. This is reference FX, not a
bank execution quote or a guaranteed settlement rate.

Official contracts consulted:

- https://openexchangerates.org/signup/free — current account/plan limits.
- https://docs.openexchangerates.org/reference/authentication — supports the
  `Authorization: Token ...` header; credentials need not appear in request URLs.
- https://docs.openexchangerates.org/reference/latest-json — USD base, publication
  timestamp and numeric rates. Latest means the latest permitted by the plan.
- https://docs.openexchangerates.org/reference/historical-json — historical
  publication dates are UTC; avoid historical `symbols` plan restrictions by
  fetching the snapshot and filtering locally.
- https://docs.openexchangerates.org/reference/supported-currencies — current
  symbols are distinct from historical currency availability.
- https://frankfurter.dev/ — evaluated as a keyless alternative. V2 supports
  central-bank sources and blended rates, with provider/date coverage that needs
  explicit pair-by-pair acceptance. No automatic fallback or source mixing is
  introduced. This decision does not assert that Frankfurter lacks coverage.

## Audit findings and implementation plan

| Finding | Resulting behavior |
| --- | --- |
| Unchecked response base, empty/invalid rates | Reject non-USD, malformed, non-finite, non-positive and unrepresentable snapshots before writes |
| Float decoding and unverified publication time | Decode JSON numbers as Decimal; validate timestamp, freshness and historical UTC date |
| Credential query URLs | Header authentication; redirects refused; safe exceptions omit upstream body/URL |
| Latest snapshot relabeled with requested date | Store provider publication date, including a previous UTC day |
| Future/indefinitely old fallback rates | Never look ahead; cached fallback limited to seven days |
| Independently selected cross-rate legs | Both legs must share a publication date, including Safe-to-Spend |
| Production on-demand amplification / worker event-loop lifetime | Scheduled Compose default, cache-only scheduled conversions and atomic shared request budget; short-lived Redis clients close within each worker loop |
| Recurring worker session used after context exit | Keep reads/stamps/commit in the active session; use next occurrence, cache only, count actual changes |
| Monthly historical backfill approximation | Fetch exact candidate dates, oldest first; preserve rows that cannot yet be truthfully converted |
| Raw provider failure surfaced from refresh | Return controlled HTTP 503 for contract/provider failures |
| No operator acceptance tooling | Read-only latest/historical probe; separate CI Redis quota concurrency acceptance |

## Production configuration

Use the production secret-file mechanism from
`FINCO_PRODUCTION_SECRET_MANAGEMENT_V1.md`. Supply `OPENEXCHANGERATES_APP_ID`
through the secret store; never put a real App ID in source, committed values,
command-line arguments, frontend code or copied logs.

Required release settings:

```text
REQUIRE_FX_PROVIDER=true
FX_SYNC_MODE=scheduled
FX_ALLOW_UNSAFE_1TO1_FALLBACK=false
```

API, worker and singleton Beat must see the same settings/credential and shared
Redis. Compose defaults to scheduled; Helm development defaults remain local
friendly, but production rendering requires all three release settings. Existing
supported currency list and historical rows remain intact. No schema migration,
price change, UI replacement or currency-list reduction is part of #18.

The atomic Redis guard reserves **attempts**, not just successful responses:
maximum 24 requests per UTC day and one attempt per target date per hour across
API/workers. Attempts expire; the daily key expires after two days. A failed HTTP
request consumes its reservation. Redis failure stops new upstream calls while
cached conversions remain usable. The cap is at most 744 guarded requests in a
31-day month. Operator probes, other applications using the same key, provider
billing windows and key sharing still need dashboard quota monitoring. This is
not a claim that all requests using the account are globally controlled.

Scheduled conversions do not fetch missing history themselves. Backfill is an
operator task, oldest date first, with the same budget; rerun after the cooldown
or next day until required dates are present. Missing rates leave an existing
stamp unchanged or a new stamp NULL. Never enable the development 1:1 fallback
for production. Genuine same-currency conversion remains 1.

Historical rates represent the requested UTC day, not a monthly closing price.
Cached fallback is explicitly a recent prior observation within seven calendar
days; cross-rate legs use the same observation day. It is an estimate rather
than proof of a bank's actual transaction conversion. Safe-to-Spend stays read
only and blocks its headline when a valid common-date pair is missing.

## Acceptance steps and remaining live gates

1. Provision an operator-owned provider account; verify current plan, terms,
   commercial-use rights, currency/date coverage and quota in its dashboard.
2. Inject the real credential in the runtime secret store; confirm API/worker/Beat
   consistency without printing it. Confirm UTC runtime date semantics. FX resolution and quota dates use UTC explicitly.
3. With production configuration, run the read-only probes:

   ```sh
   python -m scripts.verify_production_fx
   python -m scripts.verify_production_fx --historical-date 2025-06-15
   ```

   Both require a valid USD snapshot covering all configured supported currencies.
   They print only provider/date/count and never write financial rows. Requests
   consume account quota even though they bypass the application's sync budget.
4. Run one scheduled sync against the intended database; independently verify
   publication date, source, supported coverage, idempotent unique-date upserts,
   and unchanged unrelated financial rows.
5. Verify worker/Beat schedule, then conversions for USD/INR, INR/USD and a
   non-USD cross-pair from the same snapshot. Verify unavailable/stale/different
   dates block truthful conversion and Safe-to-Spend instead of inventing money.
6. Exercise provider outage/429 and Redis outage in a controlled deployment;
   inspect redacted logs, cached behavior and recovery after cooldown.
7. Confirm historical import dates, recurring next occurrence and resumable
   legacy NULL/1:1 healing with a provider-backed snapshot.

Actual production account, App ID, quota dashboard, deployment DB sync and outage
acceptance remain pending until their evidence exists. Do not mark these complete
from HTTP mocks, local SQLite or green GitHub CI.

## Verification checklist

- [x] Provider contract tests cover Decimal parsing, base/date/freshness, invalid
  rates, HTTP errors, safe logs and redirect refusal.
- [x] Conversion regression tests cover look-ahead, stale caches, mismatched
  dates, publication-date persistence and scheduled cache-only reads.
- [x] Recurring regression checks active session, cache-only stamping and disposal.
- [x] Safe-to-Spend regression rejects independently dated FX legs.
- [x] Read-only production provider acceptance command supplied.
- [x] CI Redis concurrency acceptance checks 100 competing requests produce
  exactly 24 reservations, duplicate denial and key TTLs.
- [x] Local backend suite: 4,199 passed, 7 skipped, 91.32% coverage (Python 3.12.14).
  Final focused suite: 149 passed; Ruff and complete backend `ty check .` passed.
  Worker-client lifecycle and DB precision-boundary regressions were added
  after full-suite collection and are covered by the final focused suite; PR CI
  verifies the complete final tree. The precision-boundary test first reproduced
  the issue, then passed after validation was tightened.
- [ ] PR CI green; reviewed commit merged to main.
- [ ] Live acceptance gates above supplied with real provider/deployment evidence.
