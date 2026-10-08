# Original #48: SimpleFIN classification

## Audit and contract

Base main: 4fb4a06ffdf00df22e609cb61f8f503b9307f232. The adapter defaulted every
account to checking; type overrides already persist across sync and card
overrides reverse the internal storage sign. No historical provenance separates
an automatic checking default from a user-selected checking type.

Official protocol reviewed 2026-10-08: https://www.simplefin.org/protocol.html
Account fields have no standardized account type. Balance and available balance
are separate observations; neither names nor signs establish classification.
The protocol does not establish a universal card/loan balance-sign convention.
No undocumented `extra` or name heuristics are trusted.

## Implementation and verification plan

1. Import unclassified accounts as unknown, preserving signed booked balance.
2. Migration 108 changes only ambiguous SimpleFIN checking types to unknown;
   retain identity, balance, history, explicit other types and other providers.
   Existing genuine checking accounts require one explicit re-selection.
3. Existing workspace-authorized edit path confirms a type; subsequent sync
   preserves it. Add SimpleFIN-only loan edits, signed like ordinary accounts;
   card edits reverse storage sign while preserving signed economic position.
   Do not invent credit limit, APR, installment or loan repayment records.
4. Display Unclassified and a classification explanation in all 15 locales.
   Loan edits remain available only for SimpleFIN; Enable Banking loans remain
   provider-owned. Unknown rename submits no unsupported type.
5. Reject missing/nonfinite balances and malformed/duplicate identifiers instead
   of making zero balances or incomplete account inventories.
6. Verify parser, scoped edits, signed ledger, repeat sync, migration scope and
   rollback protections. Run local checks and all seven exact feature CI jobs,
   native PostgreSQL proof, guarded merge, then all seven fresh-main jobs.

## Boundaries

Unknown accounts are not cash for Safe-to-Spend. Existing SimpleFIN provider
block remains even after manual classification: user choice is not live bank
verification or a freshness guarantee. Positive loan observations are retained
as signed positions; no universal debt-sign claim is made. Native SQL uses
synthetic HTTP, not real banking. Original #46 live acceptance remains paused.
