# Production FX cache provenance

Production FX resolution and Safe-to-Spend now accept cached rows only when
their source matches the configured Open Exchange Rates adapter. Positive
numeric values and recent publication dates alone do not approve a manually
inserted or unattributed conversion. Exact-date lookups, common-date fallback,
closest-rate reads and the spending-plan reader enforce the same rule.

An approved prior snapshot can still be used within the existing seven-day
window. Different publication dates cannot be mixed. Unapproved cache rows
remain stored; no historical transactions, amounts or existing conversion
stamps are rewritten. Same-currency conversions remain exact without a cache.
Development/test installations keep their existing fixture behavior.

Manual balance confirmations and spending-plan dates now use the UTC day,
matching provider publication dates and the documented confirmation contract,
even if the server's local calendar day differs.

The source label is an ingestion attribution, not cryptographic proof of an
upstream response. Actual provider credentials, dated sync, runtime configuration,
worker operation and live outage acceptance still require independent evidence.
This change performs no provider requests or database migrations and does not
complete the production database conversion or authorize cutover.
