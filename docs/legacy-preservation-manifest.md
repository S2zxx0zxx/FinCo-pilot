# Legacy conversion preservation gate

The recovered legacy database has 58 tables, including provider, AI, deletion,
payment and planning state beyond the core users/accounts/transactions. A
three-table converter would silently omit that history. The saved restore
evidence must be independently validated rather than trusting a supplied
`all_58_tables_match` flag.

Run from `backend/`, with the recovery evidence's protected local file path:

```sh
python scripts/legacy_preservation_manifest.py /path/to/recovery-evidence.json
```

The tool is offline and imports no application settings or DB driver. It checks
that source catalogue, source fingerprints and restored fingerprints cover the
same exact table set, with no duplicate tables/columns, valid nonnegative row
counts and 64-character SHA-256 values. Every table's count and fingerprint must
match an independent restore branch. Failure produces sanitized JSON and exit 1.
Success prints metadata only, retaining every table and source column in an
explicit unmapped preservation plan, and binds the manifest to the exact input
file's SHA-256. No SQL or conversion is executed.

Users to users, financial_accounts to accounts, and transactions to transactions
are proposals requiring field review, not approved transforms. Unknown tables
remain visible. The report always keeps conversion_ready and cutover_authorized
false: restore proof alone cannot establish identity/session, workspace,
financial balance, transaction flags, encryption, objects or deletion semantics.
Empty tables also require a reviewed schema/state disposition. The evidence date
is historical; running this offline tool does not refresh production observations.

Before any conversion, obtain a fresh protected read-only catalogue/fingerprint
snapshot, reconcile every source column, agree how unknown balances are represented,
and exercise the actual converted application and rollback on an isolated branch.
The original source remains unchanged. This artifact prepares a reviewable gate;
it does not complete the master prompt's database conversion or production cutover.
