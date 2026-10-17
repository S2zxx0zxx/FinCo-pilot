import { pageMetadata } from '@/lib/page-metadata'
import { MarketingDocument } from '@/components/marketing-document'
import { landingAsset } from '@/lib/asset'

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
    <section><h2>CSV or QIF: what the current importer preserves</h2>
      <p>The current application accepts CSV, QIF, OFX/QFX and CAMT files. Format support does not mean every bank’s export will map correctly. CSV offers column and amount-sign controls; QIF offers a date-format selector because day/month order can be ambiguous.</p>
      <p>In the reviewed QIF parser, the date, amount and payee or memo supply the transaction details. Extra reference tags are not mapped to an external transaction ID. Do not assume a UPI reference will survive QIF import as a searchable unique ID. When both payee and memo exist, the payee supplies the description.</p>
      <p><a href={landingAsset('/samples/transactions-example.csv')} download>Download two synthetic INR rows</a> to inspect your mappings. The sample has ₹1,000 income and ₹250 expense: net flow ₹750, with no claim about the account balance.</p>
    </section>
    <section><h2>When two similar payments are not duplicates</h2>
      <p>For an imported row with an external ID, the current duplicate check compares the destination account, external ID and date. Without that ID, it compares account, date, amount, credit/debit type and description (including the original description).</p>
      <p>Two legitimate payments with identical values on those fields can match. A changed description can also cause a repeated row to stop matching. CSV exposes a duplicate-detection option; other formats keep detection enabled. Review excluded rows against the source statement before applying a file. This check is not a guarantee of safe repeated or concurrent imports.</p>
    </section>
    <section><h2>Verify the result</h2><p>Compare row counts, signs and totals with the source file. Reconcile the transaction history against a reliable balance source. Do not delete unrelated records or reset an account to make an import appear successful.</p></section>
    <section><h2>Does importing require a bank connection?</h2><p>File-based workflows are separate from provider bank synchronization. Availability of an importer, a bank provider or a specific file format must be checked in the active application. This guide does not promise universal bank support.</p></section>
    <section><h2>Review basis and limitations</h2>
      <p>Technical content reviewed on 17 October 2026 against the <a href="https://github.com/S2zxx0zxx/FinCo-pilot/blob/264a6ad75ef588f70402a7b1a44ca9b167840262/backend/app/services/import_service.py">versioned importer implementation</a> and <a href="https://github.com/S2zxx0zxx/FinCo-pilot/blob/264a6ad75ef588f70402a7b1a44ca9b167840262/frontend/src/pages/import.tsx">import review controls</a>. Your deployed version may differ. No claim of bulk-import limits, uninterrupted availability, universal reference preservation or personal financial advice is made.</p>
    </section>
  </MarketingDocument>
}
