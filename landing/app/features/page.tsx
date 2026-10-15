import { pageMetadata } from '@/lib/page-metadata'
import Link from 'next/link'
import { MarketingDocument } from '@/components/marketing-document'

export const metadata = pageMetadata('/features', 'Accounts, transactions and budgets | FinCo-Pilot', 'Explore FinCo-Pilot workflows for organizing accounts, importing transactions, reviewing budgets and understanding reports, with availability and data limitations explained.')

export default function FeaturesPage() {
  return <MarketingDocument path="/features" title="A workspace for your financial picture" intro="Start with your records, organize the details and review the patterns. Organize accounts, review imports and explore budgets and reports. Available modules and connections depend on your app settings and plan.">
    <section><h2>Keep accounts organized</h2><p>Manual accounts give you a place to organize financial records without treating a live bank connection as a prerequisite. Account type, currency and balance history matter: an imported transaction history alone may not establish today’s available balance.</p></section>
    <section><h2>Import and review transactions</h2><p>The import workflow includes file preview, column mapping and a review step. Check date formats, money signs, currency and duplicate handling before applying an import. Use a synthetic file first when learning the workflow.</p><Link href="/guides/import-transactions">Read the transaction import guide</Link></section>
    <section><h2>Plan budgets and goals</h2><p>Budget and goal modules help organize planned spending and saving. Review the underlying records and enabled modules before relying on a summary. A plan is a record of your choices, not a promise of savings or a substitute for financial advice.</p></section>
    <section><h2>Understand reports and spending estimates</h2><p>Reports depend on the records, categories, dates and currencies included. Spending-plan estimates also depend on current balances, upcoming obligations and the reserves you review. Leave an unknown balance unconfirmed rather than inventing a number.</p></section>
    <section><h2>Know the boundaries</h2><p>Bank connectivity and optional AI capabilities depend on configured providers and eligibility. This page does not promise support for a specific bank, country, UPI connection or regulated advice. Read the live application’s pricing and policies before choosing a plan.</p><Link href="/how-it-works">See the first-session checklist</Link></section>
  </MarketingDocument>
}
