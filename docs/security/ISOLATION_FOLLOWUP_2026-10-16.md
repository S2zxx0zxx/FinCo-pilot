# Financial isolation follow-up — 16 October 2026

Base: latest main `9e9fbefbc79c180a201e6fd789ee701c3aac1f3e`, after security PR #91 merged as `93de92ba951f5a4bdce4a8aacd9b6b5ff74ddaa5`. This is source/test evidence, not an actual production rollout or universal security certification.

## Research and acceptance plan

OWASP API1 requires authorization for each dereferenced object identifier; API3 separately covers writable and returned properties. An authenticated route or a workspace header alone does not prove either. Review both the outer record and IDs supplied in request bodies, nested resources, list/search/export queries and background-action boundaries.

Primary references:
- https://owasp.org/API-Security/editions/2023/en/0xa1-broken-object-level-authorization/
- https://owasp.org/API-Security/editions/2023/en/0xa3-broken-object-property-level-authorization/
- https://cheatsheetseries.owasp.org/cheatsheets/Insecure_Direct_Object_Reference_Prevention_Cheat_Sheet.html

Use unrelated synthetic A/B users, each with an owned business workspace and a legitimate test entitlement. Mint real application JWTs; do not override authentication, workspace resolution, service lookups or permission dependencies. Positive owner controls must succeed, then negative reads/writes must deny access and preserve victim records. Preserve legitimate explicit workspace membership and cross-workspace group sharing. Native tests run only against the existing guarded disposable PostgreSQL target; never point them at customer data.

## Reproduced defects and changes

Before fixes, seven HTTP negative cases failed: budget foreign category, recurring foreign category create/update, asset foreign wallet create/update, category foreign group create/update. The handlers accepted those cross-workspace references with 201/200. Shared reference validation now checks ID and workspace before mutation; asset create/buy/import validation runs before market-provider I/O. Null/unlink behavior remains supported.

An eighth regression reproduced a workspace write escape: the recurring generation endpoint selected rows only by creator. A person writable in workspace A could trigger a recurring row they originally created in B after being downgraded to viewer in B. The request path now passes the selected workspace into the query. Trusted CLI/Celery generation retains its existing explicitly unscoped scheduler mode; it is not an externally supplied bypass flag.

Nested category-group loading and wallet rollups now restrict children to the parent's workspace. Category-group joins in category visibility/budget comparison, and wallet joins in asset-import warnings, include workspace equality. These read defenses do not migrate, erase or silently repair malformed historical customer records.

## Controlled coverage

| Surface | New controlled checks |
|---|---|
| Accounts, categories/category groups, payees, wallets/assets, budgets/goals, collections, recurring entries, transactions/rules, groups, loans, invoices | Own list positives; unrelated A/B IDs absent; cross-tenant edits/deletes denied; victim record retained; spoofed body user/workspace fields cannot relocate created records. Loans reject unknown fields by existing schema. |
| Account summaries/history/bills; transaction details/transfer pair/candidates/attachments; asset details/values/trends/trades; goals/payees/loans/invoices; group details/members/transactions/balances/settlements | Positive own reads; foreign and nonexistent object handling. Category rule-usage intentionally returns an empty own-workspace rule set for unknown/foreign IDs; its positive control contains the owner's actual rule. Existing status contracts are preserved. |
| Search, transaction CSV, workspace backup | Owner canary present, unrelated canaries absent; forged foreign workspace header denied. |
| Bulk transaction category/tag/delete actions | Foreign-only IDs affect zero rows; victim transaction unchanged. |
| Linked financial references | Foreign account/category/payee/goal target/rule action/invoice counterparty denied according to each existing API's 400/404 contract; valid and null edits preserved. |
| Connections, import logs, transaction attachments, investment trade children | Synthetic own records visible; foreign records/actions denied; private connection credential marker absent; unauthorized attachment/provider I/O not reached. |
| Shared workspace roles | Explicit viewer reads existing workspace records, cannot write; promoted editor can write. |
| Historical malformed links | Foreign category child excluded from victim group; foreign asset excluded from wallet totals; budget output does not expose foreign group name. |
| Recurring generation | Selected writable workspace cannot generate a creator-owned row in another workspace where that person is now only a viewer. |

`backend/tests/test_financial_tenant_isolation.py` is added to both the full backend suite and a native PostgreSQL CI step. Existing invoice allocation/attachment, reconciliation, split/settlement, shared-transaction, deletion, write-gate and native role-contention regressions remain required in the full suite. A parameterized test count is not a claim that every possible data state or serialization property has been exhaustively enumerated.

## Evidence and remaining boundaries

Initial focused suite: 22 passed after the seven reference fixes. Expanded intermediate run: 45 passed and one test-contract mismatch (category rule-usage returns empty 200 rather than 404); contract corrected with a nonempty positive control. Recurring escape failed before fix (generated one foreign-workspace row), then passed with the selected-workspace filter. Three improvement tests passed. Final matrix, feature regression and exact-head full/native CI outcomes are recorded on the new follow-up PR; pending runs are not passes.

Real deployed database binding/schema, provider sessions, historical customer-data integrity, staging A/B acceptance and production release remain separate gates. No production record, permission, key, schema, cloud resource or deployment changed in this work. Secrets/artifact review is the next work item in the same PR; absence of a pattern finding never proves a complete secret-free history.

## Follow-up verification and identity regression

Final local A/B matrix: **51 passed in 103.66 seconds**. Existing affected feature regressions: **190 passed**. Candidate `cc131f4` native PostgreSQL matrix: **51 passed in 176.17 seconds**, in addition to seven financial reports, 18 directory/upload checks and the existing actual disposable encrypted restore/role-race proofs. Full backend CI on that candidate had 5,263 passed/seven skipped and one existing main-branch Clerk ownership failure; it was not all green.

Latest main's `9e9fbef` had changed Clerk to implicitly attach any verified email to an existing local UUID. That contradicted the existing safety regression (expected 403, actual 200). The follow-up preserves already mapped sign-in and new-account signup, and automatically bridges only an independently stored exact legacy issuer/subject pair. An email-only existing account still needs independently approved identity mapping; no production mapping is invented or rewritten. New exact/partial/inactive legacy-binding regressions and Clerk API tests: **22 passed locally**. These identity tests are also added to guarded native PostgreSQL CI. Exact-head full CI remains required after these additions.

Item 2's bounded source/history/artifact review and its limits are recorded in `SECRET_REVIEW_2026-10-16.md` in the same PR #96.
