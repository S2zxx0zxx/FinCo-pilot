# Secret and artifact review — 16 October 2026

This continues item 2 in the same PR as the financial-isolation fixes. No credential values, private environment values or customer data are copied into this report. No credential was rotated, history rewritten or artifact deleted.

## Research and plan

GitHub's primary guidance distinguishes finding/removing a committed value from revoking it: an actual exposed credential must be revoked/rotated at its provider. Merely deleting a file or trusting log masking is not clearance. Review source context, reachable history and actual artifact bytes separately; fail closed on incomplete artifact reads and never execute/extract an artifact while inspecting it.

- https://docs.github.com/en/code-security/concepts/secret-security/secret-scanning
- https://docs.github.com/en/code-security/how-tos/manage-security-alerts/manage-secret-scanning-alerts/resolving-alerts
- https://docs.github.com/en/actions/reference/security/secure-use
- https://docs.github.com/en/actions/concepts/workflows-and-actions/workflow-artifacts

## Results and their exact scope

| Check | Evidence |
|---|---|
| Current repository hygiene | Passed after removing whole-line example/synthetic-marker suppression. Known credential patterns no longer disappear merely because an example word occurs elsewhere on the line. |
| Default detect-secrets 1.5.0, no online verification | 2,459 candidates / 121 files. |
| Same detector with all heuristic filters disabled | 4,086 candidates / 154 candidate files; 1,558 text files inspected, 78 binary files excluded, zero files above the 8 MiB source limit. |
| Candidate context disposition | Every row of that snapshot is classified in the value-free CSV; zero unclassified contexts. This combines programmatic classification with structural/source-context review, not an independent human attestation or a live provider credential-validity test. |
| Locally reachable Git history | 8,890 reachable objects; 3,519 text blobs and 1,019 commit/tag objects inspected against six families without marker suppression. 101 binary objects excluded; zero objects above 2 MiB excluded; zero pattern findings. Remote-only/unreachable/deleted refs are not certified. |
| Actual downloaded baseline artifacts | All ten archives from successful `bd7f8c3` core, public-entry, landing and pricing runs downloaded. Every SHA-256 matched GitHub's artifact digest. Nineteen text files inspected; 60 binary members excluded; zero six-family findings or read/limit errors. See exact IDs and digests in the JSON inventory. |
| Controlled local built assets | 280 text files inspected, 51 binary files excluded, 12,595,508 bytes read; zero six-family findings/read errors. This local build is not a deployed-artifact attestation. |

The classification includes public source/content digests and resource IDs (2,386), package integrity metadata (1,037), public translation copy (350), synthetic test contexts (225), reviewed config references/development placeholders (32), non-secret addresses/versions (22), guarded disposable CI proof inputs (20), non-secret code constants (13) and scanner-version metadata (1). Examples of structural false positives: a retention evidence key mistaken for an IBM key, fiscal checksum alphabets, a public historical KDF salt, public deployment IDs and the audit report's own digest fields. A contextual fixture/placeholder label does not attest that an operator never reused it in a deployment.

## Improvements built and tested

`check_secret_hygiene.py` no longer exempts an entire line based on words such as `example` or `synthetic`. A regression constructs a credential-shaped test value and proves that adding those words does not suppress the finding; output does not reveal the value.

`check_artifact_secret_hygiene.py` inspects ZIPs, files and built asset directories offline. It does not extract paths or print matched values/filenames. It bounds member size, cumulative bytes and inventory; encrypted, missing, unreadable or oversized input produces errors rather than a clean result. Binary files are explicitly excluded. Three boundary tests passed, including a traversal-shaped ZIP member, redacted finding output and decompression byte limits.

CI now inspects built public assets. Coverage must pass inspection before upload, including when the test run itself failed. These are bounded six-family pattern guards, not a substitute for the broader detector/context review or runtime secret management.

## Integration failures preserved

The first follow-up CI found two existing latest-main regressions: explicit `any` in Sentry's beforeSend failed lint, and verified-email Clerk auto-linking failed the existing account-ownership regression. Sentry now uses the SDK's contextual event type, preserving the sanitizer. Clerk keeps existing exact ExternalAuthIdentity mappings and bridges only an independently stored exact legacy issuer/subject binding; verified email alone cannot attach an existing financial UUID. Brand-new provisioning is retained. Local Clerk API/ownership suite: 22 passed. Final exact-head full/native/browser results are recorded on PR #96; pending runs are not passes.

## Remaining external acceptance

No newly confirmed production credential was identified in this bounded review, so no speculative rotation or history rewrite was performed. Actual runtime secret ownership/validity/rotation dates and private environment metadata were not exposed by the connected GitHub tools and remain NOT VERIFIED. Artifact inspection does not include OCR of screenshots, every historical/private run or arbitrary unknown credential formats. Actual deployed secret injection and owner review remain distinct from source/CI proof. If a real exposed credential is established later, provider revocation/rotation is required; removing a repository line alone is insufficient.

Evidence: `evidence/secret-context-triage-2026-10-16.csv`, `evidence/secret-review-summary-2026-10-16.json`, `evidence/history-pattern-scan-2026-10-16.json`, `evidence/artifact-inspection-2026-10-16.json`.
