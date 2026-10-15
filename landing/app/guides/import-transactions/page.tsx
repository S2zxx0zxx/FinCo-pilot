import { pageMetadata } from '@/lib/page-metadata'
import { MarketingDocument } from '@/components/marketing-document'

export const metadata = pageMetadata('/guides/import-transactions', 'Preview and review a CSV transaction import | FinCo-Pilot', 'Learn how to prepare a small synthetic CSV, review date and amount mappings, check duplicates and avoid treating incomplete transaction history as an account balance.')

export default function ImportGuidePage() {
  return <MarketingDocument path="/guides/import-transactions" title="Review a transaction import before applying it" intro="A file import is a proposed change to your records. Use the preview to check the interpretation before confirming it. Start with a small synthetic file to learn the importer before using real financial records.">
    <section><h2>Prepare a small example</h2><p>The following rows are synthetic. They demonstrate a date, description, signed amount and currency. They do not represent a customer or an actual account.</p>
      <pre tabIndex={0} role="region" aria-label="Synthetic CSV example"><code>{'date,description,amount,currency\n2026-10-01,Sample grocery,-25.00,USD\n2026-10-02,Sample income,100.00,USD'}</code></pre>
      <p>If interpreted as signed amounts, these rows have a net flow of USD 75. That does not establish the account’s current balance: the opening balance and any missing records are still unknown.</p></section>
    <section><h2>Check the destination account</h2><p>Confirm the intended account, account type and currency. Keep workspaces separate. Use only records you are authorized to import and a synthetic test account when learning a new importer.</p></section>
    <section><h2>Match columns and dates</h2><p>Map date, description and amount to the corresponding columns. A date such as 03/04 can be ambiguous; confirm the preview’s interpretation rather than assuming a regional format. If the file has separate inflow and outflow columns, inspect the appropriate mapping controls.</p></section>
    <section><h2>Inspect signs and currency</h2><p>Check one known expense and one income row. Use the amount-sign controls only after understanding the preview. Do not treat a currency code as proof of conversion or supply a guessed exchange rate. Mixed-currency records require an appropriate, supported conversion workflow.</p></section>
    <section><h2>Review duplicates and failed rows</h2><p>Reimporting an overlapping period can create duplicates if identifiers or mapping differ. Review the importer’s duplicate options, exclusions and failed-row details. Correct a small example and preview again before confirming; do not repeatedly submit a failing file.</p></section>
    <section><h2>Verify the result</h2><p>Compare row counts, signs and totals with the source file. Reconcile the transaction history against a reliable balance source. Do not delete unrelated records or reset an account to make an import appear successful.</p></section>
    <section><h2>Does importing require a bank connection?</h2><p>File-based workflows are separate from provider bank synchronization. Availability of an importer, a bank provider or a specific file format must be checked in the active application. This guide does not promise universal bank support.</p></section>
  </MarketingDocument>
}
