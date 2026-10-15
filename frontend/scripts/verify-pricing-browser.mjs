/** Frontend-only contract rendering checks. ALL API responses below are fixtures.
 * This script is never imported by the app. It does not verify a real backend,
 * login, payment, bank connection or AI service, and sends no external writes.
 */
import { spawn } from 'node:child_process'
import { mkdir, writeFile } from 'node:fs/promises'
import { chromium, firefox, webkit } from 'playwright'
import AxeBuilder from '@axe-core/playwright'
import assert from 'node:assert/strict'

const output = process.env.PRICING_QA_OUTPUT
const port = 4276
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

const results = []
let browser
try {
  const engine = process.env.PRICING_QA_BROWSER || 'chromium'
  browser = await ({chromium,firefox,webkit}[engine]).launch({headless:true})
  if(output) await mkdir(output,{recursive:true})
  for(const signedIn of (process.env.PRICING_QA_ACCOUNT_ONLY ? [true] : [false,true])) {
    for(const theme of ['light','dark']) {
      const context = await browser.newContext({viewport:{width:390,height:1000},serviceWorkers:'block',reducedMotion:'reduce'})
      await context.addInitScript(({theme,signedIn})=>{localStorage.setItem('theme',theme);if(signedIn)localStorage.setItem('token','frontend-contract-fixture');localStorage.setItem('workspace_id','frontend-qa-workspace');localStorage.setItem('onboarding_completed','true')},{theme,signedIn})
      let writes=0
      await context.route('**/*',async route=>{
        const req=route.request(),url=new URL(req.url())
        if(url.origin!==`http://127.0.0.1:${port}`){await route.abort();return}
        if(req.method()!=='GET'){writes++;await route.fulfill({status:405,body:'Mutations forbidden'});return}
        if(!url.pathname.startsWith('/api/')){await route.continue();return}
        await route.fulfill({status:200,contentType:'application/json',body:JSON.stringify(fixed[url.pathname]??[])})
      })
      const page=await context.newPage(),errors=[]
      page.on('pageerror',e=>errors.push(e.message))
      for(const width of [320,375,390,620,768,920,921,1024,1440]){
        await page.setViewportSize({width,height:1000})
        await page.goto(`http://127.0.0.1:${port}/pricing?plan=pro`,{waitUntil:'networkidle'})
        await page.getByRole('heading',{name:'A plan for where you are. And what’s next.'}).waitFor()
        const overflow=await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth+1)
        if(overflow && output){await page.screenshot({path:`${output}/overflow.png`,fullPage:true});await writeFile(`${output}/overflow.json`,JSON.stringify(await page.evaluate(()=>[...document.querySelectorAll('body *')].filter(el=>el.getBoundingClientRect().right>innerWidth+1).map(el=>({tag:el.tagName,class:el.getAttribute('class'),text:el.textContent?.slice(0,80),right:el.getBoundingClientRect().right}))),null,2))}
        assert.equal(overflow,false,`overflow ${width} ${theme} signedIn=${signedIn}`)
        await page.getByRole('radio',{name:'Annual'}).click()
        const summary=page.getByRole('region',{name:'Selected plan'})
        await summary.getByText('₹999',{exact:true}).waitFor()
        if(width<=920){
          const tab=page.getByRole('tab',{name:'Pro',exact:true});await tab.focus();await page.keyboard.press('ArrowRight')
          await page.locator('[role=tab][aria-selected=true]').filter({hasText:'Max'}).waitFor()
        }else await page.getByRole('button',{name:'Select Max',exact:true}).click()
        await summary.getByText('₹349',{exact:true}).waitFor()
        await summary.getByText('/ month',{exact:true}).waitFor()
        assert.match(page.url(),/interval=annual/)
        await page.getByRole('button',{name:'Does selecting a plan charge me?'}).click()
        await page.getByText(/No. Selecting a plan only updates/).waitFor()
        if(width===390||width===1440){
          const axe=await new AxeBuilder({page}).analyze()
          if(output && axe.violations.length){await writeFile(`${output}/axe-failure.json`,JSON.stringify(axe.violations,null,2));await page.screenshot({path:`${output}/failure.png`,fullPage:true})}
          assert.deepEqual(axe.violations.map(v=>({id:v.id,nodes:v.nodes.map(n=>n.target)})),[],`axe ${width} ${theme} signedIn=${signedIn}`)
          if(output)await page.screenshot({path:`${output}/pricing-${width}-${theme}-${signedIn?'account':'guest'}.png`,fullPage:true})
        }
        results.push({engine,width,theme,signedIn,annualPro:999,maxMonthly:349,overflow:false})
      }
      // Public annual choice must survive the auth handoff without submitting a form.
      if(!signedIn){
        await page.goto(`http://127.0.0.1:${port}/pricing?plan=pro&interval=annual`,{waitUntil:'networkidle'})
        await page.getByRole('button',{name:'Sign in for Pro'}).click()
        await page.waitForURL('**/login?**')
        const next=new URL(page.url()).searchParams.get('next')
        assert.equal(next,'/pricing?plan=pro&interval=annual')
      }else{
        await page.goto(`http://127.0.0.1:${port}/pricing?plan=free`,{waitUntil:'networkidle'})
        await page.getByRole('link',{name:'Manage subscription'}).click()
        assert.match(page.url(),/#billing-management$/)
      }
      assert.equal(writes,0);assert.deepEqual(errors,[])
      await context.close()
    }
  }
  if(output)await writeFile(`${output}/results.json`,JSON.stringify({mode:'local-contract-fixtures',results},null,2))
  console.log(`Pricing acceptance: ${results.length} visits; keyboard, annual/auth handoff, Max monthly, FAQ, comparison, no overflow; axe 8 scans; no external writes.`)
} finally { await browser?.close();server.kill() }
