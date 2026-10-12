# Current manual amounts in Safe-to-Spend

An imported receipt or partial posted history is net flow, not a verified opening or present-day account balance. Checking the obligations checkbox must not silently turn that flow into cash.

Manual cash accounts and cards now require an explicit current amount for each calculation. Unknown inputs remain blank; the corresponding aggregate and spending headline remain null. Explicit zero is valid. Cash can be negative (overdraft); outstanding card debt is non-negative and reserved without using credit limits. Inputs are finite two-decimal amounts, account-currency denominated and bound to the calculation's UTC date, supported active manual accounts and current workspace. They cannot override bank-connected accounts or claim bank verification.

This calculation does not write accounts, ledger entries, identity rows or migrations. Pending expenses and obligations retain their conservative reserves. User-confirmed figures remain estimates, not authenticated bank evidence. Rates, loan fee/floating/partial/prepayment conventions and all production-master acceptance gates remain separate requirements.

UI clears confirmation/result state on workspace changes, ignores late inventory results, prevents calculation when inventory cannot load and prevents editing inputs while calculation is pending. Hindi copy and Unknown rendering preserve the existing finance UI. Restore/rehearsal/cutover and live provider acceptance are not claimed completed by this fix.
