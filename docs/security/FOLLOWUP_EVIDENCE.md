# Pre-merge follow-up evidence, 15 October 2026

Previous exact candidate: `9017d0709721c6f63e33867c9ab8e8175556927c`.
- [CI 38737025795](https://github.com/S2zxx0zxx/FinCo-pilot/actions/runs/38737025795): all seven jobs success.
- [Advisory 38737025653](https://github.com/S2zxx0zxx/FinCo-pilot/actions/runs/38737025653): success.
- Local final backend: 5,194 passed, seven native-only skips, 348.12 seconds.

Follow-up source changes and test paths:

| Scope | Regression | Initial result | Fixed result |
|---|---|---|---|
| Existing storage limits before reads/billing/decode | `backend/tests/test_storage_upload_budget.py` | Three failures | Three pass in combined 12-test rerun |
| Knowledge raw error/path/provider/traceback privacy; parser state | `backend/tests/test_agents_ingest.py` | Four failures, including stricter existing embed assertion | Included in 145-test focused run and 12-test final rerun |
| Persisted document/agent queue binding | same | One failure | Pass in final 12-test rerun |
| Native role downgrade contention | `backend/scripts/verify_role_downgrade_postgres.py` | New native acceptance proof | Pending first CI execution at commit time |

Whole-backend Ruff and ty passed after follow-up changes. Final full backend run is in progress at commit time. Final outcomes are recorded on PR #91; this timestamped source document does not turn a pending run into a verified result.

No data migration, provider activation, customer record query, production change, merge or deployment performed. Storage payload limits do not bound multipart spooling, parser CPU/decompression or concurrent uploads. Knowledge parser handling does not sandbox a decoder. Native race tests are not an exhaustive permission audit. Real-provider, exact-runtime, production-backup, contracts, legal identity and human attestation gates remain open.

A further optional-provider log review reproduced three additional failures in `backend/tests/test_optional_provider_log_privacy.py` (holdings, credit-card bills, market search). Those fallbacks now log safe exception classes, without raw provider text, stack traces, connection/account identifiers or search queries; institution-logo fallback follows the same rule. Full affected bank-service/market/ingestion/storage suite: **145 passed in 36.60 seconds**. These are three further failing regression cases, separate from the eight above. Whole-backend Ruff/ty passed again.

## Error-boundary and deployment-log follow-up

Further boundary regressions reproduced four failures before fixes: unexpected custom-agent SSE error text, bank-worker result error text, production error traceback/token path, and source traceback policy. A separate raw-access-log entrypoint contract also failed before its fix. Runtime fixed checks pass: broad affected provider/market/support/Clerk/agent suite **113 passed**; final boundary/Pluggy/MCP/entrypoint suite **35 passed** (including extra safe-warning/response-body properties). A SimpleFIN compatibility assertion initially failed because its documented `act.failed` category disappeared; the code now preserves that allowlisted category while suppressing unknown codes, messages and account fields; the assertion was retained and passes. Whole-backend Ruff and ty passed.

- Custom-agent unexpected stream failures are generic, as Core failures already were. Conversation/title success and normal executor categories remain.
- Bank-worker stored job errors and returned task errors use safe retry/reconnect messages; status/reconnection branches and exception propagation inside the service are retained. Background task result payloads no longer echo arbitrary exceptions.
- Application and MCP logger calls no longer request raw exception tracebacks; source regression contract guards that policy. This prevents our log calls from serializing SQL parameters or HTTP URL exceptions, but does not attest every third-party/runtime sink. Source templates are inventoried in `evidence/application-log-sites.json`.
- Provider fallback logs omit raw exception messages, response bodies and unknown SimpleFIN warning codes; market queries and a growth-rule financial amount are removed from affected logs. Authentication verification decisions are unchanged; Clerk verification logging keeps only the exception class.
- Production error correlation uses route templates, not raw token-bearing paths, retaining opaque FC request references. Dev/test exception propagation remains.
- Docker image, development/QA/production Compose commands and both Helm services now use `--no-access-log`; metrics and application audit/reference logs remain. Real runtime log/forensics and retention acceptance is still required before release. No live log settings were changed.
- The role-downgrade and native storage-budget proof **passed** on intermediate `77d3097`, native PostgreSQL job 116446980953 / CI run 38742341693. A later complete local backend run on intermediate `7aa764d` returned **5,204 passed / 7 native-only skips**, 372.22 seconds; this does not substitute for the final boundary-source run.

Final complete local/backend coverage CI for the final source snapshot is required separately; final results are recorded on PR #91. Production/provider/legal gates remain open.
