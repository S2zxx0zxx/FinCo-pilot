import { chromium } from 'playwright'
import sharp from 'sharp'
import { mkdir, writeFile } from 'node:fs/promises'
import { createHash } from 'node:crypto'
import { execFileSync } from 'node:child_process'

// Loopback-only specimen capture of the ORIGINAL Vite application. Every API
// response below is synthetic. No real credential, customer data or backend.
const origin = process.env.PRODUCT_CAPTURE_ORIGIN || 'http://127.0.0.1:4173'
if (!['127.0.0.1', 'localhost'].includes(new URL(origin).hostname))
  throw new Error('Capture requires an isolated loopback app')
const dir = new URL('../public/product/', import.meta.url)
await mkdir(dir, { recursive: true })
const user = {
  id: 'sample-user',
  email: 'sample@example.invalid',
  is_active: true,
  is_verified: true,
  is_superuser: false,
  is_2fa_enabled: false,
  preferences: {
    language: 'en',
    locale: 'en-IN',
    currency_display: 'INR',
    display_name: 'Alex',
    theme: 'dark',
  },
}
const workspace = {
  id: 'sample-workspace',
  name: 'Personal workspace',
  kind: 'personal',
  is_archived: false,
  default_currency: 'INR',
  locale: 'en-IN',
  tax_jurisdiction: 'IN',
  role: 'owner',
  icon: 'wallet',
  color: '#9edcaa',
  created_at: '2026-10-01',
  created_by_user_id: user.id,
  managed_by_user_id: null,
  enabled_modules: [
    'transactions',
    'accounts',
    'import',
    'reports',
    'assets',
    'budgets',
    'goals',
    'recurring',
    'categories',
    'payees',
    'split_groups',
    'rules',
    'invoices',
  ],
}
const accounts = [
  ['Everyday account', 84250, 'checking'],
  ['Savings account', 100000, 'savings'],
].map(([name, balance, type], i) => ({
  id: 'sample-account-' + i,
  user_id: user.id,
  connection_id: null,
  external_id: null,
  name,
  display_name: null,
  masked_number: null,
  institution_name: null,
  institution_logo_url: null,
  type,
  balance,
  current_balance: balance,
  previous_balance: balance - 5000,
  balance_primary: balance,
  currency: 'INR',
  credit_limit: null,
  available_credit: null,
  statement_close_day: null,
  payment_due_day: null,
  next_close_date: null,
  next_due_date: null,
  minimum_payment: null,
  card_brand: null,
  card_level: null,
  is_closed: false,
  closed_at: null,
}))
const categories = [
  {
    id: 'food',
    name: 'Groceries',
    icon: 'ShoppingCart',
    color: '#8cbb8a',
    type: 'expense',
    group_id: null,
  },
  {
    id: 'salary',
    name: 'Salary',
    icon: 'Briefcase',
    color: '#8eaac0',
    type: 'income',
    group_id: null,
  },
]
const transactions = [
  ['Monthly income', 42000, 'income', 'salary', '2026-10-01'],
  ['Grocery market', 2480, 'expense', 'food', '2026-10-08'],
].map(([description, amount, type, category_id, date], i) => ({
  id: 'sample-transaction-' + i,
  user_id: user.id,
  account_id: accounts[0].id,
  category_id,
  category_name: category_id === 'food' ? 'Groceries' : 'Salary',
  category_icon: category_id === 'food' ? 'ShoppingCart' : 'Briefcase',
  category_color: '#8cbb8a',
  description,
  amount,
  amount_primary: amount,
  type,
  currency: 'INR',
  date,
  status: 'posted',
  is_ignored: false,
  is_shared: false,
  attachment_count: 0,
  tags: [],
  notes: null,
  payee_id: null,
  group_id: null,
  installment_number: null,
  total_installments: null,
}))
const fixtures = {
  '/api/users/me': user,
  '/api/workspaces': [workspace],
  '/api/workspaces/current': workspace,
  '/api/accounts': accounts,
  '/api/collections': [],
  '/api/categories': categories,
  '/api/category-groups': [],
  '/api/payees': [],
  '/api/groups': [],
  '/api/goals/summary': [],
  '/api/goals': [],
  '/api/transactions': {
    items: transactions,
    total: transactions.length,
    page: 1,
    limit: 500,
  },
  '/api/dashboard/summary': {
    total_balance: { INR: 184250 },
    total_balance_primary: 184250,
    projected_balance: { INR: 196730 },
    projected_balance_primary: 196730,
    balance_date: '2026-10-12',
    monthly_income: 42000,
    monthly_expenses: 2480,
    monthly_income_primary: 42000,
    monthly_expenses_primary: 2480,
    projected_income: 42000,
    projected_expenses: 14500,
    accounts_count: 2,
    pending_categorization: 0,
    pending_categorization_amount: 0,
    assets_value: { INR: 0 },
    assets_value_primary: 0,
    primary_currency: 'INR',
    pending_shares_net: 0,
  },
  '/api/dashboard/spending-by-category': [
    {
      category_id: 'food',
      category_name: 'Groceries',
      category_icon: 'ShoppingCart',
      category_color: '#8cbb8a',
      total: 2480,
      projected_total: 6400,
      percentage: 100,
    },
  ],
  '/api/dashboard/balance-history': {
    current: Array.from({ length: 12 }, (_, i) => ({
      day: i + 1,
      balance: 172000 + i * 1113.64,
    })),
    previous: Array.from({ length: 31 }, (_, i) => ({
      day: i + 1,
      balance: 160000 + i * 380,
    })),
  },
  '/api/dashboard/projected-transactions': [],
  '/api/budgets/comparison': [],
  '/api/budgets': [],
  '/api/connections': [],
  '/api/connections/providers': [],
  '/api/recurring': [],
  '/api/billing/entitlements': {
    plan: 'free',
    capabilities: {},
    limits: {},
    usage: {},
  },
  '/api/billing/founder-campaign': { live: false },
  '/api/billing/catalog': null,
}

const extended = process.env.PRODUCT_CAPTURE_EXTENDED === 'true'
if (extended) {
  fixtures['/api/billing/entitlements'] = {
    plan: 'pro',
    status: 'active',
    capabilities: { advanced_reports: true },
    limits: {},
    usage: {},
  }
  fixtures['/api/assets'] = []
  fixtures['/api/asset-groups'] = []
  fixtures['/api/currencies'] = [
    { code: 'INR', symbol: '₹', name: 'Indian Rupee', flag: 'IN' },
  ]
  fixtures['/api/budgets'] = [
    {
      id: 'sample-budget',
      user_id: user.id,
      category_id: 'food',
      amount: 8000,
      month: '2026-10-01',
      is_recurring: true,
    },
  ]
  fixtures['/api/goals'] = [
    {
      id: 'sample-goal',
      user_id: user.id,
      name: 'Emergency reserve',
      target_amount: 100000,
      current_amount: 60000,
      currency: 'INR',
      target_amount_primary: 100000,
      current_amount_primary: 60000,
      target_date: null,
      tracking_type: 'manual',
      account_id: null,
      asset_id: null,
      asset_group_id: null,
      status: 'active',
      icon: 'shield',
      color: '#477552',
      position: 0,
      metadata_json: null,
      created_at: '2026-10-01',
      updated_at: '2026-10-01',
      percentage: 60,
      monthly_contribution: null,
      on_track: null,
      account_name: null,
      asset_name: null,
      asset_group_name: null,
    },
  ]
  fixtures['/api/recurring-transactions'] = [
    {
      id: 'sample-recurring',
      user_id: user.id,
      account_id: accounts[0].id,
      category_id: 'food',
      description: 'Monthly household supplies',
      amount: 4000,
      currency: 'INR',
      type: 'debit',
      frequency: 'monthly',
      weekend_adjustment: 'none',
      day_of_month: 25,
      start_date: '2026-10-01',
      end_date: null,
      is_active: true,
      auto_generate: false,
      next_occurrence: '2026-10-25',
      amount_primary: 4000,
      fx_rate_used: 1,
    },
  ]
  fixtures['/api/reports/net-worth'] = {
    summary: {
      primary_value: 184250,
      change_amount: 20000,
      change_percent: 12.18,
      breakdowns: accounts.map((a) => ({
        key: a.id,
        label: a.name,
        value: a.balance,
        color: '#8cbb8a',
      })),
    },
    trend: Array.from({ length: 6 }, (_, i) => ({
      date: `2026-${String(i + 5).padStart(2, '0')}-01`,
      value: 164250 + i * 4000,
      breakdowns: { cash: 164250 + i * 4000 },
      change: i === 0 ? null : 4000,
    })),
    meta: {
      type: 'net_worth',
      series_keys: ['cash'],
      currency: 'INR',
      interval: 'monthly',
    },
    composition: accounts.map((a) => ({
      key: a.id,
      label: a.name,
      value: a.balance,
      color: '#8cbb8a',
      group: 'Cash',
    })),
    category_trend: [],
  }
}
const browser = await chromium.launch({ args: ['--no-sandbox'] })
const report = {
  sourceCommit: execFileSync('git', ['rev-parse', 'origin/main'], {
    encoding: 'utf8',
  }).trim(),
  frontendAppTree: execFileSync('git', ['rev-parse', 'HEAD:frontend/src'], {
    encoding: 'utf8',
  }).trim(),
  buildLabel: null,
  data: 'Synthetic browser fixtures; not live account data',
  captures: [],
  unmapped: [],
}
try {
  for (const [name, path] of extended
    ? [
        ['budgets', '/budgets'],
        ['goals', '/goals'],
        ['recurring', '/recurring'],
        ['reports', '/reports'],
      ]
    : [
        ['dashboard', '/'],
        ['accounts', '/accounts'],
      ]) {
    for (const width of [1440, 390]) {
      const context = await browser.newContext({
        viewport: { width, height: width === 390 ? 900 : 920 },
        reducedMotion: 'reduce',
      })
      await context.addInitScript(() => {
        localStorage.setItem('token', 'synthetic-capture-only')
        localStorage.setItem('i18nextLng', 'en')
        localStorage.setItem('theme', 'dark')
      })
      await context.route('**/*', async (route) => {
        const url = new URL(route.request().url())
        if (!['127.0.0.1', 'localhost'].includes(url.hostname))
          return route.abort()
        if (url.pathname.startsWith('/api/')) {
          const data = fixtures[url.pathname]
          if (data === undefined) {
            report.unmapped.push(url.pathname)
            return route.fulfill({
              status: 404,
              contentType: 'application/json',
              body: JSON.stringify({ detail: 'No specimen fixture' }),
            })
          }
          if (data === null)
            return route.fulfill({
              status: 503,
              contentType: 'application/json',
              body: '{"detail":"Pricing intentionally absent in specimen"}',
            })
          return route.fulfill({
            status: 200,
            contentType: 'application/json',
            body: JSON.stringify(data),
          })
        }
        return route.continue()
      })
      const page = await context.newPage()
      const errors = []
      page.on('pageerror', (e) => errors.push(e.message))
      await page.goto(origin + path, { waitUntil: 'networkidle' })
      await page.evaluate(() => document.fonts.ready)
      await page.waitForTimeout(300)
      const skip = page.getByRole('button', { name: 'Skip tour', exact: true })
      if (await skip.isVisible()) await skip.click()
      await page.waitForTimeout(250)
      if (name === 'reports') {
        await page
          .locator('.recharts-area-curve')
          .first()
          .waitFor({ state: 'visible' })
        await page.waitForFunction(() =>
          [...document.querySelectorAll('.recharts-area-curve')].some(
            (el) => (el.getAttribute('d') || '').length > 40,
          ),
        )
        await page.waitForTimeout(1800)
      }
      if (extended)
        await page
          .getByText(
            {
              budgets: '8,000',
              goals: 'Emergency reserve',
              recurring: 'Monthly household supplies',
              reports: '1,84,250',
            }[name],
            { exact: false },
          )
          .first()
          .waitFor({ state: 'visible', timeout: 15000 })
      const body = await page.locator('body').innerText()
      const buildLabel = body.match(/Version ([^\n]+)/)?.[1] ?? null
      if (report.buildLabel && buildLabel && report.buildLabel !== buildLabel)
        throw new Error('Capture build changed during the run')
      report.buildLabel ??= buildLabel
      if (buildLabel && /^[a-f0-9]{7,40}$/.test(buildLabel)) {
        const buildTree = execFileSync(
          'git',
          ['rev-parse', buildLabel + ':frontend/src'],
          { encoding: 'utf8' },
        ).trim()
        if (buildTree !== report.frontendAppTree)
          throw new Error(
            'Build does not match the reviewed frontend source tree',
          )
        report.buildFrontendTree = buildTree
      }

      if (body.includes('Sidebar Navigation') && body.includes('Skip tour'))
        throw new Error('Onboarding overlay must be closed before capture')
      if (
        errors.length ||
        body.includes('Failed to load') ||
        body.includes('Something went wrong') ||
        page.url().includes('/login')
      )
        throw new Error(
          JSON.stringify({
            name,
            width,
            errors,
            url: page.url(),
            body: body.slice(0, 150),
          }),
        )
      if (name === 'dashboard' && !body.includes('84,250'))
        throw new Error(
          'Actual dashboard specimen did not render seeded balance: ' +
            body.slice(0, 400),
        )
      if (
        extended &&
        !body.includes(
          {
            budgets: '8,000',
            goals: 'Emergency reserve',
            recurring: 'Monthly household supplies',
            reports: '1,84,250',
          }[name],
        )
      )
        throw new Error(
          'Extended specimen missing expected content: ' +
            name +
            ' ' +
            body.slice(-1400),
        )
      const file = name + (width === 390 ? '-mobile' : '-desktop') + '.webp'
      const png = await page.screenshot({
        fullPage: false,
        animations: 'disabled',
      })
      const buffer = await sharp(png)
        .webp({ quality: 86, effort: 6 })
        .toBuffer()
      await writeFile(new URL(file, dir), buffer)
      report.captures.push({
        name,
        width,
        path,
        file,
        sourceCommit: report.sourceCommit,
        sha256: createHash('sha256').update(buffer).digest('hex'),
        pageErrors: errors,
      })
      await context.close()
    }
  }
} finally {
  await browser.close()
}
report.unmapped = [...new Set(report.unmapped)]
await writeFile(
  new URL(
    extended
      ? '../docs/PRODUCT_CAPTURE_EXTENDED.json'
      : '../docs/PRODUCT_CAPTURE_PROVENANCE.json',
    import.meta.url,
  ),
  JSON.stringify(report, null, 2) + '\n',
)
console.log(JSON.stringify(report, null, 2))
