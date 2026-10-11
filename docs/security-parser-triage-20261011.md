# XML parser security and scan triage — 2026-10-11

A fresh Bandit scan of app and mcp_server completed without scan errors and reported 33 signals. This change addresses the two untrusted XML parser findings rather than suppressing them.

CAMT financial imports and S3 inventory use defusedxml 0.7.1, with DTD, entity and external-reference processing explicitly forbidden. S3's previous ASCII byte precheck did not cover UTF-16 XML declarations; parser-level validation now rejects these before returning inventory keys. CAMT rejection returns a generic ValueError rather than disclosing an entity definition. S3 rejection is translated into the existing StorageIntegrityError. Inventory chunks are bounded before buffering; existing namespace/pagination/integrity checks remain enforced.

Eight new regression cases exercise UTF-8/UTF-16 internal entities, external entities and DTD references, including the encoded S3 bypass. Existing valid CAMT/OFX, storage and market-symbol regressions remain covered. Focused suite: 167 passed with warnings as errors; Ruff and ty passed. The locked production/development dependency audit reports no known advisories at this checkpoint.

Legacy SHA1 calls generate stable Tesouro symbols and synthetic OFX FITIDs; they do not authenticate users, sign requests or prove integrity. Explicit usedforsecurity=False preserves existing persisted identifiers and duplicate-import behavior. Replacing their outputs without a dual-identity data migration would create a financial compatibility risk. No authentication or integrity hash was weakened.

The follow-up scan reports 27 signals: no HIGH signals, two MEDIUM/LOW-confidence SQL-construction signals and 25 LOW signals. No blanket scanner ignore list was added.

| Signal | Context reviewed | Disposition / limits |
| --- | --- | --- |
| B314 XML parsing | User CAMT uploads and streamed S3 XML | Fixed with parser-level DTD/entity/external rejection and encoded-input regressions |
| B324 legacy SHA1 | Stable normalized bond symbols and generated OFX IDs | Explicit nonsecurity purpose; identifiers unchanged |
| B608 dynamic SQL, disaster_recovery | Catalogue-derived schema/table names quoted by doubling embedded double quotes | Reviewed identifier quoting; no raw user value interpolation in those queries |
| B105 apparent passwords | Bearer token-type literals, a bootstrap setting-name literal and rejection of the shipped development MCP secret | Literal identifiers/production rejection checks, not committed working credentials |
| B101 asserts | Narrow type/invariant checks after provider/order, asset lookup, scoped-installment and split validation | Not standalone authorization gates; retain explicit upstream checks. An optimized-bytecode behavior audit is not claimed complete |
| B110/B112 except pass/continue | Rollback failure privacy, uncertain payment/refund reconciliation, optional price/date/FX/logo handling | Contextual fallback signals; no blanket proof that every possible failure is covered |
| B404/B603 subprocess | Operator recovery tools, argument arrays with shell=False default, timeout, private diagnostics | Read-only review; live disaster-recovery drill still pending |
| B406 XML escape | xml.sax escaping for PDF text, not parsing untrusted XML | Safe escaping purpose; scanner import heuristic |

This is a bounded source/dependency review and specific fix, not a universal security guarantee or production release approval. Live backend configuration, legacy data conversion, secrets/provider acceptance and broader forensic gates remain unresolved.

Primary parser reference: https://github.com/tiran/defusedxml . Candidate full CI and post-merge evidence are recorded in the canonical continuity checkpoint.
