# Recovered legacy source and applied-SQL evidence

The original Vercel `financecopilot` project links to Clerk and its deployment
metadata names the separate repository `S2zxx0zxx/FinanceCopilot`. That repository
retains the pre-foundation-import source at commit
`f7c492211787e32faa3dbf2fe6bfff8071a72d59` (parent of import `f495b9b`). This
supersedes the earlier assumption that no legacy source was available. The user
does not need to provide that source again.

Read-only rehearsal `schema_migrations` has 29 applied SQL filenames/checksums.
23 files match the recovered checkout's bytes directly. Six files 023–027 match
exactly after reconstructing CRLF line endings. The original migration runner
hashes UTF-8 file contents with SHA-256; the reconstruction reproduces the actual
recorded hashes. This is stronger than a filename or schema-shape match. The
checkout also contains 029_profile_avatar_presets.sql, which is NOT in the
observed applied history and must not be assumed applied.

From `backend/`, compare a protected metadata-only JSON history export against
the recovered migrations directory:

```sh
python scripts/verify_legacy_migration_sources.py /path/to/history.json /path/to/backend/db/migrations
```

The offline checker rejects incomplete checksums, duplicate/path-escaping
filenames, outside-directory symlinks, missing files and any source mismatch.
It accepts only exact original/LF/CRLF byte reconstructions matching the stored
SHA-256, reports unapplied SQL, and executes no SQL or application imports.
Passing this check does not establish current schema or converted app readiness.

## Source contracts now grounded

- `users.user_id` is the internal UUID. Migration013 adds clerk_uid;
  migration018 makes firebase_uid nullable. Legacy lookup checks both subject
  columns; current provider issuer/subject verification is still required.
- Transaction amounts are positive integer paise, with debit/credit carrying
  direction. Source records are immutable, corrections additive, and duplicate,
  tombstone, review, transfer and settlement semantics must be retained.
- Legacy FinancialStateRepo excludes duplicate/deleted/needs_review rows and
  restricts its balance query to INR. Posted balance is posted credits minus
  posted debits; pending debits reduce availability and pending credits do not.
- That calculation is a ledger-derived net flow. It supplies no bank opening
  balance or proof of complete transaction history. Mapping it to a known
  current Account.balance would conflate different financial meanings.
- The source's getCoverageMetrics assumes every active account is synced. This
  assumption is not acceptable provider proof for the new application.
- The recovered SessionService revocation methods contain scaffold behavior.
  Do not carry its return-true behavior into the hardened current auth stack.

Old project metadata includes Clerk, OmniRouter/Gemini, R2, queue and Setu keys.
Production/preview values are Sensitive and were not returned by env reads;
development's readable public Clerk key is a TEST key, not production acceptance.
No old keys were copied into production, no source SQL was rerun and no source
financial/identity rows were exposed. Source state and provider metadata are
evidence for the mapping review, not permission to reuse unverified identities.
