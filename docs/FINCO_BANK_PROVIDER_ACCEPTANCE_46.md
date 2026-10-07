# International bank provider acceptance — original roadmap 46

Audited base main: c0cdbfdc246c0b3406b84d3354198968cf1c882f. User explicitly deferred Indian AA step40 and authorized46;40–45 are not complete.

## Existing implementation and verified gaps

Pluggy widget, Enable Banking OAuth, SimpleFIN token adapters already exist. Connection routes enforce workspace ownership; Redis OAuth state is single use; background sync tracks queued/running/terminal status. Transactions, accounts, sync freshness and dashboard consumers already exist. Reuse these components.

Enable Banking balance HTTP failures currently fall back to zero, missing/malformed balances also become zero, and details failures can skip accounts while the sync is stamped successful. Session expiry swallowed at these points cannot produce the existing reconnect outcome. Initial session accounts represented as strings are skipped rather than fetched. These are observable source gaps, not claims of live provider tests.

## Primary sources

- https://enablebanking.com/docs/api/reference/ — session/account details/balances/transactions, response statuses.
- https://enablebanking.com/docs/faq/ — missing balances, consent expiry, session-specific account identifiers, restricted own-account access versus public production contract/KYB.
- https://www.simplefin.org/protocol.html — balance-date, errors, pending transactions and credential-bearing access URLs.
- https://docs.pluggy.ai/en/docs/connections/item-lifecycle — partial success is distinct from complete institutional refresh.

## Implementation and acceptance plan

1. Fail closed on Enable Banking account details/balance transport or expiry failure. Fetch all account observations before the service mutates balances; existing service rollback preserves prior financial records.
2. Require nonempty bound account ID, complete details, finite numeric balance and currency consistent with the account. Missing balances are unavailable, not zero. An actual numeric zero remains valid. No liability classification changes (#47).
3. Support initial session string IDs by fetching their details; validate details identify the requested account. Never import partial account inventory as a completed observation.
4. Preserve typed expiry and rate-limit signals for existing worker status/reconnect behavior; safe public diagnostics exclude raw provider bodies and credential/session-bearing paths.
5. Adversarial HTTP MockTransport regressions: 401/410/429/5xx, absent/invalid/nonfinite balances, different account identity/currency, second-account failure, true zero, string-ID onboarding. Fixtures are synthetic, not live bank acceptance.
6. Service-level retained balance/history/freshness rollback regression; all existing provider, connections, worker, dashboard/Safe-to-Spend and UI checks. Full lint/type/build, final exact-head seven CI jobs, guarded merge/tree proof and fresh-main all seven precede engineering acceptance.
7. Actual live acceptance separately requires an authorized configured deployment, supported bank account, consent and provider access. Never inspect or print secrets, initiate arbitrary bank consent, claim free/public access from a registered adapter, or mark46 live-complete from CI.

## Live verification record requirements

For each selected provider record environment and deployment commit, authorized connection, masked account count/currencies, provider-observed balance and dates, complete paginated transactions, repeat-sync duplicate invariance, dashboard reconciliation/freshness, expired/reconnect and disconnect behavior. Keep evidence private and minimal; no raw financial export or credential in this document. Existing local disconnect is not universal upstream revocation; verify provider-specific consent removal separately. Sandbox/own-account restricted/public production are distinct acceptance states. No real live record is available in this session yet.
