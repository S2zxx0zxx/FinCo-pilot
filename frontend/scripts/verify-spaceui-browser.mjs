/** Frontend-only contract rendering checks. ALL API responses below are fixtures.
 * This script is never imported by the app. It does not verify a real backend,
 * login, payment, bank connection or AI service, and sends no external writes.
 */
import { spawn } from 'node:child_process'
import { mkdir, writeFile } from 'node:fs/promises'
import { chromium } from 'playwright'
import assert from 'node:assert/strict'

const output = process.env.SPACEUI_QA_OUTPUT
const port = 4274
const server = spawn(process.execPath, ['node_modules/vite/bin/vite.js', 'preview', '--host', '127.0.0.1', '--port', String(port)], { stdio: ['ignore', 'pipe', 'pipe'] })
await new Promise((resolve, reject) => {
  server.stdout.on('data', data => { if (data.toString().includes('Local:')) resolve() })
  server.on('error', reject)
  server.on('exit', code => reject(new Error(`Preview exited: ${code}`)))
})

const modules = ['transactions','accounts','import','reports','assets','budgets','goals','recurring','categories','payees','split_groups','rules','invoices']
const user = { id: 'frontend-qa-user', email: 'qa@example.test', is_active: true, is_superuser: true, is_verified: true, is_2fa_enabled: false, preferences: { currency_display: 'INR', language: 'en', onboarding_completed: true } }
const workspace = { id: 'frontend-qa-workspace', name: 'Frontend QA', kind: 'business', is_archived: false, default_currency: 'INR', locale: 'en', tax_jurisdiction: null, icon: 'briefcase', color: '#6366f1', created_at: '2026-01-01T00:00:00Z', created_by_user_id: user.id, managed_by_user_id: null, role: 'owner', enabled_modules: modules }
const metrics = ['total_workspaces','personal_workspaces','business_workspaces','accounts','active_budgets','active_goals','active_recurring','assets','imports_monthly','rules','active_split_groups','group_members','invoices_monthly','ai_actions_monthly','storage_bytes']
const entitlements = { plan: 'max', status: 'active', billing_interval: 'monthly', current_period_end: null, cancel_at_period_end: false, capabilities: Object.fromEntries(['advanced_reports','rules','smart_reconciliation','business_workspaces','invoices','agents_automation'].map(key => [key, true])), limits: Object.fromEntries(metrics.map(key => [key, 100])), usage: Object.fromEntries(metrics.map(key => [key, 0])), resets_at: {} }
const summary = { total_balance: {}, total_balance_primary: 0, projected_balance: {}, projected_balance_primary: 0, balance_date: '2026-01-01', monthly_income: 0, monthly_expenses: 0, monthly_income_primary: 0, monthly_expenses_primary: 0, projected_income_primary: 0, projected_expenses_primary: 0, accounts_count: 0, pending_categorization: 0, pending_categorization_amount: 0, assets_value: {}, assets_value_primary: 0, primary_currency: 'INR', pending_shares_net: 0 }
const catalog = { prices: [{plan:'free',interval:'none',amount_minor:0,currency:'INR'},{plan:'pro',interval:'monthly',amount_minor:9900,currency:'INR'},{plan:'pro',interval:'annual',amount_minor:99900,currency:'INR'},{plan:'max',interval:'monthly',amount_minor:34900,currency:'INR'}], pro_annual_saving_minor:18900,tax_display_mode:'unconfigured' }
const fixed = {
  '/api/auth/me': user,
  '/api/workspaces': [workspace],
  '/api/workspaces/current': workspace,
  '/api/workspaces/frontend-qa-workspace/stats': { members: 1, accounts: 0, transactions: 0 },
  '/api/workspaces/frontend-qa-workspace/members': [],
  '/api/auth/oidc/config': { enabled: false, local_auth_enabled: true, passkey_enabled: false },
  '/api/setup/status': { has_users: true, setup_available: false, minimum_password_length: 8 },
  '/api/admin/registration-status': { enabled: true },
  '/api/admin/default-colors': { light: null, dark: null },
  '/api/admin/accounting-mode': { mode: 'cash' },
  '/api/admin/number-format': { format: 'auto' },
  '/api/admin/date-format': { format: 'auto' },
  '/api/admin/users': { items: [], total: 0 },
  '/api/info': { version: 'frontend-fixture', features: { agents: true } },
  '/api/agents/info': { enabled: true, providers: [], tools: [] },
  '/api/billing/catalog': catalog,
  '/api/billing/entitlements': entitlements,
  '/api/billing/founder-campaign': { state: 'paused', live: false, waves: [], total_capacity: 0, total_claimed: 0, total_held: 0, total_available: 0 },
  '/api/billing/checkout-status': { reservation: null, payment: null },
  '/api/dashboard/summary': summary,
  '/api/dashboard/balance-history': { current: [], previous: [] },
  '/api/transactions': { items: [], total: 0, page: 1, limit: 50, summary: { income: 0, expense: 0, net: 0, excluded: 0, currency: 'INR' } },
  '/api/transactions/calendar': { month: '2026-01', currency: 'INR', account_ids: null, days: [] },
  '/api/assets/portfolio-trend': { assets: [], trend: [] },
  '/api/invoices/summary': { outstanding: '0', overdue_amount: '0', overdue_count: 0, received_this_month: '0', buckets: { current:'0',d1_30:'0',d31_60:'0',d61_90:'0',d90_plus:'0' }, upcoming: [] },
  '/api/invoices/facets': { years: [], counts: {} },
  '/api/invoices/settings': { preset:'tracking',document_required:false,initial_state:'draft',tax_fields:'hidden',default_payment_terms_days:30,number_prefix:null,series:null,next_number:1,logo_id:null,issuer_display_name:null,footer_note:null,payment_details:null,accent_color:null,template:null },
  '/api/currencies': [{code:'INR',symbol:'₹',name:'Indian Rupee',flag:'IN'}],
  '/api/support/info': { email: null, portal_url: null, help_center_url: null },
}
const routes = ['/','/transactions','/accounts','/import','/import?tab=investments','/rules','/categories','/collections','/budgets','/recurring','/goals','/assets','/reports','/payees','/groups','/invoices','/workspace/settings','/admin','/agents','/agents/connections','/loans','/spending-plan','/pricing','/support','/accounts/missing','/groups/missing','/invoices/missing','/agents/missing','/oauth/callback','/enable-banking','/assets/import']
const publicRoutes = ['/login','/register','/forgot-password','/reset-password','/verify-email','/request-verification','/setup','/terms','/privacy','/account-deletion','/workspace-deletion','/auth/oidc/callback','/i/missing','/not-a-route']
let browser
const results = []
try {
  browser = await chromium.launch({ headless: true, args: ['--no-sandbox'] })
  if (output) await mkdir(output, { recursive: true })
  for (const width of process.env.SPACEUI_QA_QUICK ? [390] : [390,768,1024,1440]) {
    for (const theme of process.env.SPACEUI_QA_QUICK ? ['light'] : ['light','dark']) {
      const context = await browser.newContext({ viewport: {width,height:1000}, reducedMotion: 'reduce', serviceWorkers: 'block' })
      await context.addInitScript(({ theme }) => { localStorage.setItem('theme',theme);if(!sessionStorage.getItem('qa-signedout')) localStorage.setItem('token','frontend-contract-fixture');localStorage.setItem('workspace_id','frontend-qa-workspace');localStorage.setItem('onboarding_completed','true') }, {theme})
      await context.route('**/api/**', async route => {
        const request = route.request(), pathname = new URL(request.url()).pathname
        let status = 200, body = fixed[pathname] ?? []
        if(pathname==='/api/setup/status' && request.headers().referer?.includes('/setup'))body={has_users:false,setup_available:true,minimum_password_length:8}
        if (pathname.startsWith('/api/reports/')) body = { summary: {primary_value:0,change_amount:0,change_percent:null,breakdowns:[]},trend:[],meta:{type:'net_worth',series_keys:[],currency:'INR',interval:'monthly'},composition:[],category_trend:[] }
        if (/^\/api\/admin\/settings\//.test(pathname)) body = {key:pathname.split('/').at(-1),value:'false'}
        if (/^\/api\/(accounts|groups|invoices|agents)\/missing(?:\/|$)/.test(pathname)) {status=404;body={detail:'Not found'}}
        if(['/api/terms','/api/privacy-policy'].includes(pathname)){status=503;body={detail:'Fixture: policy unavailable'}}
        if (pathname.startsWith('/api/public/invoices/') || pathname.startsWith('/api/shared-invoices/') || pathname.includes('/i/missing')) {status=404;body={detail:'Not found'}}
        if (request.method() !== 'GET') {status=405;body={detail:'Frontend fixture: mutations forbidden'}}
        await route.fulfill({status,contentType:'application/json',body:JSON.stringify(body)})
      })
      const page = await context.newPage()
      let errors = []
      page.on('pageerror', error => errors.push(error.message))
      for (const path of process.env.SPACEUI_QA_QUICK ? ['/','/transactions','/pricing'] : routes) {
        errors = []
        await page.goto(`http://127.0.0.1:${port}${path}`, {waitUntil:'networkidle'})
        const state = await page.evaluate(() => ({path:location.pathname,heading:document.querySelector('h1')?.textContent,overflow:document.documentElement.scrollWidth > innerWidth + 1,boundary:document.body.innerText.includes('We could not display this page'),offenders:document.documentElement.scrollWidth>innerWidth+1?[...document.querySelectorAll('body *')].filter(el=>el.getBoundingClientRect().right>innerWidth+1).slice(0,8).map(el=>({tag:el.tagName,class:el.getAttribute('class'),right:el.getBoundingClientRect().right})):[]}))
        results.push({mode:'contract-fixtures',width,theme,requested:path,...state,errors:[...errors]})
        if(process.env.SPACEUI_QA_QUICK)console.log(JSON.stringify(results.at(-1)))
        if (output && width === 1440 && theme === 'dark' && ['/','/transactions','/pricing'].includes(path)) await page.screenshot({path:`${output}/${path === '/' ? 'dashboard' : path.slice(1)}.png`,fullPage:true})
      }
      if (width === 390) {
        await page.goto(`http://127.0.0.1:${port}/transactions`, {waitUntil:'networkidle'})
        await page.getByRole('button',{name:'Navigation',exact:true}).click()
        await page.getByRole('dialog',{name:'Navigation',exact:true}).waitFor()
        await page.keyboard.press('Escape')
        await page.getByRole('dialog',{name:'Navigation',exact:true}).waitFor({state:'hidden'})
        assert.equal(await page.locator('#finco-menu-trigger').evaluate(el=>el===document.activeElement),true,'Drawer must restore focus')
        await page.getByRole('button',{name:'User menu',exact:true}).click()
        await page.getByRole('menuitem',{name:'Delete personal account',exact:true}).waitFor()
        await page.keyboard.press('Escape')
      }
      await context.clearCookies()
      await page.evaluate(()=>{localStorage.removeItem('token');sessionStorage.setItem('qa-signedout','true')})
      for (const path of process.env.SPACEUI_QA_QUICK ? ['/login','/account-deletion'] : publicRoutes) {
        errors=[]
        await page.goto(`http://127.0.0.1:${port}${path}`,{waitUntil:'networkidle'})
        const state=await page.evaluate(()=>({path:location.pathname,heading:document.querySelector('h1')?.textContent,overflow:document.documentElement.scrollWidth>innerWidth+1,boundary:document.body.innerText.includes('We could not display this page'),offenders:document.documentElement.scrollWidth>innerWidth+1?[...document.querySelectorAll('body *')].filter(el=>el.getBoundingClientRect().right>innerWidth+1).slice(0,8).map(el=>({tag:el.tagName,class:el.getAttribute('class'),right:el.getBoundingClientRect().right})):[]}))
        results.push({mode:'public-contract-fixtures',width,theme,requested:path,...state,errors:[...errors]})
        if(['/login','/register'].includes(path))assert.equal(state.path,path,'Public auth screen must be checked signed out')
        if(output && path==='/login' && (width===390||width===1440))await page.screenshot({path:`${output}/login-${width}-${theme}.png`,fullPage:true})
      }
      console.log(`Checked ${width}px ${theme}: ${process.env.SPACEUI_QA_QUICK ? 5 : routes.length+publicRoutes.length} route visits`)
      await context.close()
    }
  }
  if(output)await writeFile(`${output}/results.json`,JSON.stringify(results,null,2))
  const failures=results.filter(row=>row.errors.length||row.boundary||row.overflow)
  console.log(JSON.stringify({visits:results.length,failures},null,2))
  assert.equal(failures.length,0,'Frontend fixture sweep found rendering/overflow regressions')
} finally { await browser?.close();server.kill() }
