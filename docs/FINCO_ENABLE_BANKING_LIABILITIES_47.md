# Enable Banking liability mapping — original roadmap 47

Audited main: fc34cdbe359d0b2498b752341cbd3cc01c4a1e73. User explicitly paused original46 LIVE acceptance and selected47. No actual bank access or live acceptance is inferred.

Primary contract: https://enablebanking.com/docs/api/reference/ — CashAccountType distinguishes CACC/CASH/SVGS from CARD/LOAN and unspecified OTHR; BalanceStatus distinguishes booked CLBD/ITBD from available credit balances. The public schema does not establish one universal liability sign convention. https://enablebanking.com/docs/faq/ describes bank-specific data availability.

Plan and accounting policy:
1. Map explicit LOAN to a provider-only loan account, never checking. Reject missing/malformed/unknown/OTHR classification instead of guessing cash. Cash classification remains explicit; never infer from names/products or balance sign.
2. Require CLBD/ITBD booked balances for loan/card accounts. Never use credit limit, available balance or transaction sum as outstanding debt. Conservatively reserve the absolute booked magnitude: card uses existing positive-debt representation, loan uses signed negative-debt representation. Zero remains zero. This can overstate a credit position; it cannot create spendable cash. No universal bank sign guarantee or repayment schedule is claimed.
3. Fresh successful complete inventory repairs legacy liability-as-cash rows in place; stable IDs/history/closed-account intent retained. Missing classification aborts the entire sync and preserves prior state. No speculative migration of legacy values; stale rows remain blocked from Safe-to-Spend until separately reconciled.
4. Prevent Enable Banking user edits across the liability boundary; cash-to-savings overrides remain available. Label loan accounts distinctly in UI; display-name edits remain available. No fabricated APR, maturity, installment or Loan-service record.
5. Test positive/negative/zero debt, booked-vs-available selection, unspecified types, failed inventory, legacy resync identity/deduplication, signed aggregate balances, safe-to-spend blockers and edit protection. Add real PostgreSQL proof using synthetic provider HTTP. All7 feature CI, guarded merge and all7 fresh-main CI precede engineering acceptance.

Existing Enable Banking/SimpleFIN Safe-to-Spend blockers remain. Original46 is paused pending authorized actual provider access; SimpleFIN classification is separate48. Synthetic tests are not live banking evidence.
