import { readFile, writeFile } from 'node:fs/promises'
const source = await readFile(
  new URL('../../backend/app/billing/pricing.py', import.meta.url),
  'utf8',
)
const frontend = await readFile(
  new URL('../../frontend/src/billing/catalog.ts', import.meta.url),
  'utf8',
)
const prices = [
  ...source.matchAll(
    /PriceOption\(\s*PlanId\.(FREE|PRO|MAX),\s*BillingInterval\.(NONE|MONTHLY|ANNUAL),\s*([\d_]+)\s*\)/g,
  ),
].map(([, plan, interval, value]) => ({
  plan: plan.toLowerCase(),
  interval: interval.toLowerCase(),
  amount_minor: Number(value.replaceAll('_', '')),
  currency: 'INR',
}))
const frontendPrices = [
  ...frontend.matchAll(
    /\{\s*plan: '([^']+)',\s*interval: '([^']+)',\s*amount_minor: ([\d_]+),\s*currency: '(INR)'\s*\}/g,
  ),
].map(([, plan, interval, amount, currency]) => ({
  plan,
  interval,
  amount_minor: Number(amount.replaceAll('_', '')),
  currency,
}))
if (
  prices.length !== 4 ||
  JSON.stringify(prices) !== JSON.stringify(frontendPrices)
) {
  throw new Error('Standard price catalog needs a reviewed marketing mapping')
}
const data =
  JSON.stringify(
    { source: 'backend/app/billing/pricing.py', prices },
    null,
    2,
  ) + '\n'
const target = new URL('../lib/standard-plans.json', import.meta.url)
if (process.argv.includes('--check')) {
  if ((await readFile(target, 'utf8')) !== data)
    throw new Error('Marketing catalog snapshot is stale')
} else await writeFile(target, data)
