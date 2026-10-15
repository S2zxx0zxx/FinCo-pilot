import { pageMetadata } from '@/lib/page-metadata'
import Link from 'next/link'
import { APP_LINKS } from '@/lib/links'
import { MarketingDocument } from '@/components/marketing-document'

export const metadata = pageMetadata('/how-it-works', 'Getting started with your financial workspace | FinCo-Pilot', 'A practical checklist for accessing FinCo-Pilot, starting with manual records, reviewing imports and checking balances and permissions.')

export default function HowItWorksPage() {
  return <MarketingDocument path="/how-it-works" title="Start with one useful financial task" intro="You do not need to begin by connecting every account. Learn the workspace with a small set of records, check the result and expand only when the information is reliable.">
    <section><h2>1. Check access and policies</h2><p>Use the application’s existing sign-up or login flow. Additional sign-in steps may be required. If access fails, use the available recovery or support options; do not create a replacement identity to reach existing financial records.</p><a href={APP_LINKS.privacy}>Read the application privacy notice</a></section>
    <section><h2>2. Start with a manual account</h2><p>Choose the correct account type and currency. For an initial walkthrough, use clearly synthetic sample data. Record actual current balances only when you have a reliable source; a partial history is not proof of the opening or current balance.</p></section>
    <section><h2>3. Preview a small import</h2><p>Check a few rows before importing a larger file. Inspect dates, income and expense signs, categories, currency and duplicates. Review the proposed records before confirming any change.</p><Link href="/guides/import-transactions">Follow the import checklist</Link></section>
    <section><h2>4. Review one budget or report</h2><p>Choose one question, such as how transactions are categorized for a month. Check the date range, included accounts and currency assumptions. Budget and advanced reporting availability can depend on module settings and plan permissions.</p></section>
    <section><h2>5. Confirm the information before acting</h2><p>A dashboard or spending estimate is only as complete as its inputs. Check missing accounts, upcoming bills, debt and reserves. For decisions needing personalized financial advice, consult an appropriately qualified professional.</p></section>
  </MarketingDocument>
}
