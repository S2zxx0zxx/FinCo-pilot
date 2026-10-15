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
