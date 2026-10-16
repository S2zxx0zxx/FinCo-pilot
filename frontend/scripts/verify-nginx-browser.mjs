/** Actual nginx production-template acceptance with synthetic GET-only API.
 * Does not certify live Clerk, bank, payments, financial data or physical devices.
 * NGINX_BIN may point to a locally compiled nginx. No app credentials required.
 */
import assert from 'node:assert/strict'
import { spawn, spawnSync } from 'node:child_process'
import { mkdir, mkdtemp, readFile, writeFile } from 'node:fs/promises'
import http from 'node:http'
import path from 'node:path'
import os from 'node:os'
import { chromium, firefox, webkit } from 'playwright'
import AxeBuilder from '@axe-core/playwright'

const work = await mkdtemp(path.join(os.tmpdir(), 'finco-nginx-'))
const output = process.env.FINCO_PERF_OUTPUT || work
await mkdir(output, { recursive: true })
await mkdir(path.join(work, 'logs'), { recursive: true })
const publicConfig = {
  '/api/auth/oidc/config': { enabled: false, local_auth_enabled: true, passkey_enabled: false },
  '/api/setup/status': { has_users: true, setup_available: false, minimum_password_length: 8 },
  '/api/admin/registration-status': { enabled: true },
  '/api/info': { features: { agents: false } },
  '/api/admin/default-colors': { light: null, dark: null },
  // These are unauthenticated public GET contracts, not private entitlements.
  '/api/billing/catalog': { prices: [{ plan: 'free', interval: 'none', amount_minor: 0, currency: 'INR' }], pro_annual_saving_minor: 0, tax_display_mode: 'unconfigured' },
  '/api/billing/founder-campaign': { state: 'paused', live: false, waves: [], total_capacity: 0, total_claimed: 0, total_held: 0, total_available: 0 },
}
const backend = http.createServer((request, response) => {
  const endpoint = new URL(request.url, 'http://localhost').pathname
  response.setHeader('Content-Type', 'application/json')
  if (request.method !== 'GET') response.writeHead(405).end(JSON.stringify({ detail: 'Test fixture: writes forbidden' }))
  else if (publicConfig[endpoint]) response.end(JSON.stringify(publicConfig[endpoint]))
  else response.writeHead(401).end(JSON.stringify({ detail: 'Test fixture: authentication required' }))
})
await new Promise(resolve => backend.listen(0, '127.0.0.1', resolve))
const backendOrigin = `http://127.0.0.1:${backend.address().port}`
const probe = http.createServer()
await new Promise(resolve => probe.listen(0, '127.0.0.1', resolve))
const port = probe.address().port
await new Promise(resolve => probe.close(resolve))
const origin = `http://127.0.0.1:${port}`
const dist = path.resolve(process.env.FINCO_PERF_DIST || 'dist')
const labOnly = process.env.FINCO_PERF_LAB_ONLY === 'true'
let template = await readFile(process.env.FINCO_PERF_TEMPLATE || 'default.conf.template', 'utf8')
template = template.replace('listen 8080;', `listen 127.0.0.1:${port};`)
  .replaceAll('/usr/share/nginx/html', dist)
  .replaceAll('/etc/nginx/finco-security-headers.conf', path.resolve('security-headers.conf'))
  .replaceAll('/var/log/nginx/access.log', path.join(work, 'access.log'))
  .replaceAll('${NGINX_RESOLVER}', '127.0.0.1')
  .replaceAll('${BACKEND_URL}', backendOrigin)
  .replaceAll('${FINCO_TRUSTED_TYPES_REPORT_ONLY}', process.env.FINCO_TRUSTED_TYPES_REPORT_ONLY === 'true' ? 'true' : 'false')
const cspMaps = (await readFile('node_modules/.cache/finco-security/csp-map.conf.template', 'utf8')).replaceAll('${FINCO_STRICT_CSP_MODE}', process.env.FINCO_STRICT_CSP_MODE || 'compatibility')
const localUser = process.getuid?.() === 0 ? 'user root root;' : ''
const config = `${localUser} daemon off; master_process off; pid ${work}/nginx.pid; error_log ${work}/error.log;
events { worker_connections 1024; }
http { types { text/html html; text/css css; application/javascript js; application/json json; image/png png; image/svg+xml svg; font/woff2 woff2; text/plain txt; }
keepalive_timeout 5s;
client_body_temp_path ${work}/client; proxy_temp_path ${work}/proxy; fastcgi_temp_path ${work}/fastcgi; uwsgi_temp_path ${work}/uwsgi; scgi_temp_path ${work}/scgi;
${cspMaps}
${template}
}`
const configPath = path.join(work, 'nginx.conf')
await writeFile(configPath, config)
const executable = process.env.NGINX_BIN || 'nginx'
const checked = spawnSync(executable, ['-t', '-p', `${work}/`, '-c', configPath], { encoding: 'utf8' })
assert.equal(checked.status, 0, checked.stderr || checked.error?.message)
const nginx = spawn(executable, ['-p', `${work}/`, '-c', configPath], { stdio: ['ignore', 'pipe', 'pipe'] })
let browser
const results = []
// Persist each operation before awaiting it: CI cancellation must leave the
// exact blocked phase, even when Playwright never returns an exception.
const startedAt = Date.now()
async function phase(name, detail = {}) {
  const progress = { phase: name, ...detail, elapsedMs: Date.now() - startedAt }
  console.log('Browser acceptance phase', JSON.stringify(progress))
  await writeFile(path.join(output, 'progress.json'), JSON.stringify(progress, null, 2))
}
try {
  let ready = false
  for (let attempt = 0; attempt < 30; attempt++) {
    try { ready = (await fetch(origin)).ok; if (ready) break } catch { /* startup */ }
    await new Promise(resolve => setTimeout(resolve, 100))
  }
  assert(ready, await readFile(path.join(work, 'error.log'), 'utf8'))
  if (!labOnly) {
    const html = await (await fetch(origin + '/index.html')).text()
    assert(!html.includes('/@vite/client') && !html.includes('/src/main.tsx'))
    const script = html.match(/<script[^>]+src="([^"]+)"/)?.[1]
    assert(script)
    for (const endpoint of ['/', '/login', '/index.html', '/sw.js', '/manifest.webmanifest', script, '/robots.txt', '/llms.txt', '/.well-known/ai-catalog.json', '/ai-catalog.json']) {
      const response = await fetch(origin + endpoint, { headers: { 'X-Forwarded-Proto': 'https' } })
      assert.equal(response.status, 200, endpoint)
      assert.equal(response.headers.get('x-frame-options'), 'DENY', endpoint)
      assert.equal(response.headers.get('x-content-type-options'), 'nosniff', endpoint)
      assert.equal(response.headers.get('cross-origin-opener-policy'), 'same-origin-allow-popups', endpoint)
      assert.equal(response.headers.get('strict-transport-security'), 'max-age=31536000', endpoint)
      assert.match(response.headers.get('content-security-policy') || '', /frame-ancestors 'none'/, endpoint)
    }
    assert.equal((await fetch(origin)).headers.get('strict-transport-security'), null, 'No HSTS on plain local HTTP')
    assert.match((await fetch(origin + script)).headers.get('cache-control'), /immutable/)
    assert.match((await fetch(origin + '/sw.js')).headers.get('cache-control'), /no-store/)
    assert.match((await fetch(origin + '/reset-password?token=synthetic')).headers.get('cache-control'), /no-store/)
    for (const endpoint of ['/static/missing.js', '/src/main.tsx', '/node_modules/missing.js', '/@vite/client', '/.vite/manifest.json']) assert.equal((await fetch(origin + endpoint)).status, 404, endpoint)
    assert.match((await fetch(origin + '/robots.txt')).headers.get('content-type'), /text\/plain/)
    const catalog = await (await fetch(origin + '/.well-known/ai-catalog.json')).json()
    assert.equal(catalog.specVersion, '1.0')
    assert.deepEqual(catalog.entries, [])

    const proxyUrl = process.env.FINCO_BROWSER_PROXY === 'true' && process.env.HTTPS_PROXY ? new URL(process.env.HTTPS_PROXY) : null
    const proxy = proxyUrl ? { server: proxyUrl.origin, username: decodeURIComponent(proxyUrl.username), password: decodeURIComponent(proxyUrl.password), bypass: '127.0.0.1,localhost' } : undefined
    const browserName = process.env.FINCO_ENTRY_BROWSER || 'chromium'
    browser = await ({chromium,firefox,webkit}[browserName]).launch({ headless: true, args: browserName==='chromium' ? ['--no-sandbox'] : [], proxy })
    // Public marketing must be delivered before the finance SPA or auth SDK.
    const redirect = await fetch(origin + '/?token=synthetic-private', { redirect: 'manual' })
    assert.equal(redirect.status, 302)
    assert.equal(redirect.headers.get('location'), '/welcome/', 'Proxy-safe relative redirect required')
    for (const width of [320, 390, 768, 1440]) {
      const context = await browser.newContext({ viewport: { width, height: 1000 }, reducedMotion:'reduce', serviceWorkers:'block' })
      const page = await context.newPage(), errors = [], api = []
      page.on('pageerror', error => errors.push(error.message))
      await page.addInitScript(() => { window.__fincoCspViolations=[];document.addEventListener('securitypolicyviolation', event => window.__fincoCspViolations.push(event.effectiveDirective)) })
      page.on('request', request => { if(new URL(request.url()).pathname.startsWith('/api/'))api.push(request.url()) })
      await context.route('**/*', route => new URL(route.request().url()).origin === origin ? route.continue() : route.abort())
      await phase('marketing-navigation', { width })
      await page.goto(origin, { waitUntil:'networkidle' })
      assert.equal(new URL(page.url()).pathname, '/welcome/')
      await page.getByRole('heading',{level:1}).waitFor()
      await page.getByRole('button',{name:'What is FinCo-Pilot?',exact:true}).waitFor()
      assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth+1),false)
      assert.equal(await page.getByRole('heading',{level:1}).count(),1)
      assert.deepEqual(api,[], 'Marketing must not request auth/financial APIs')
      assert(!await page.locator('script[src*="/static/index-"]').count(),'Marketing loaded finance SPA')
      if(width===320||width===390){
        await page.getByRole('button',{name:'Open navigation',exact:true}).click()
        await page.getByRole('navigation',{name:'Mobile navigation'}).waitFor()
        await page.keyboard.press('Escape')
        assert.equal(await page.getByRole('button',{name:'Open navigation',exact:true}).evaluate(el=>el===document.activeElement),true)
      }
      // faq-1 is deliberately open by default. Clicking it closes the answer;
      // exercise a default-closed item so hydration timing cannot invert intent.
      await page.getByText(/FinCo-Pilot is a personal finance workspace/).waitFor()
      const faq = page.getByRole('button',{name:'Can I use FinCo-Pilot on my phone?',exact:true})
      const answer = page.getByText(/The web application includes responsive screens/)
      assert.equal(await faq.getAttribute('aria-expanded'),'false')
      await faq.click()
      await answer.waitFor()
      assert.equal(await faq.getAttribute('aria-expanded'),'true')
      await faq.click()
      await answer.waitFor({state:'hidden'})
      assert.equal(await faq.getAttribute('aria-expanded'),'false')
      assert.deepEqual(errors,[])
      if(process.env.FINCO_STRICT_CSP_MODE==='enforce')assert.deepEqual(await page.evaluate(()=>window.__fincoCspViolations),[],'Marketing blocked by strict CSP')
      await phase('marketing-accessibility', { width })
      const axe=await new AxeBuilder({page}).withTags(['wcag2a','wcag2aa','wcag21aa']).analyze()
      assert.deepEqual(axe.violations.map(item=>({id:item.id,targets:item.nodes.map(n=>n.target)})),[])
      for(const target of ['/login','/register','/pricing','/privacy','/terms','/support']) assert(await page.locator(`a[href="${target}"]`).count(),`Missing same-origin CTA ${target}`)
      await page.evaluate(()=>window.scrollTo(0,0))
      await phase('marketing-screenshot', { width })
      if(width===390||width===1440)await page.screenshot({path:path.join(output,`landing-connected-${width}.png`),fullPage:true})
      results.push({mode:'public-entry',width,path:'/welcome/',apiRequests:0,axeViolations:0})
      await phase('marketing-pricing-navigation', { width })
      await page.locator('a[href="/pricing"]').last().click()
      await page.getByRole('heading',{name:'A plan for where you are. And what’s next.'}).waitFor()
      assert.equal(new URL(page.url()).pathname,'/pricing')
      if(process.env.FINCO_CONFIGURED_CLERK_CHECK!=='true'){
        await page.goto(origin+'/dashboard',{waitUntil:'domcontentloaded'})
        await page.locator('input[type=email]').waitFor()
        assert.equal(new URL(page.url()).pathname,'/login','Anonymous dashboard must stay protected')
      }
      await phase('context-close', { width })
      await context.close()
    }
    if(process.env.FINCO_CONFIGURED_CLERK_CHECK!=='true') {
      const installed=await browser.newContext({serviceWorkers:'block',reducedMotion:'reduce'})
      await installed.addInitScript(()=>{
        const original=window.matchMedia.bind(window)
        window.matchMedia=query=>{
          const result=original(query)
          if(query==='(display-mode: standalone)')Object.defineProperty(result,'matches',{value:true})
          return result
        }
      })
      const page=await installed.newPage()
      await page.goto(origin)
      await page.waitForURL('**/login')
      assert.equal(new URL(page.url()).pathname,'/login','Legacy installed root must hand off to protected app')
      await installed.close()
    }
    const missingMarketing = await fetch(origin+'/welcome/_next/static/missing.js')
    assert.equal(missingMarketing.status,404)
    assert.match(missingMarketing.headers.get('cache-control') || '',/no-store/)
    // Cold-login acceptance is a separate phase from marketing context churn.
    await phase('marketing-browser-close')
    await browser.close()
    await phase('login-browser-launch')
    browser = await ({chromium,firefox,webkit}[browserName]).launch({ headless:true, args:browserName==='chromium'?['--no-sandbox']:[], proxy })
    for (const width of [390, 768, 1024, 1440]) {
      for (const reducedMotion of ['no-preference', 'reduce']) {
        const context = await browser.newContext({ viewport: { width, height: 1000 }, reducedMotion, serviceWorkers: 'block' })
        // Production Clerk keys require the existing authorized browser origin.
        // Only the app host is served by the local GET-only nginx fixture;
        // provider HTTPS requests retain their actual host and tenant.
        const browserOrigin = process.env.FINCO_CONFIGURED_CLERK_CHECK === 'true' ? 'https://fincopilot.app' : origin
        if (browserOrigin !== origin) await context.route('https://fincopilot.app/**', async route => {
          const url = new URL(route.request().url())
          const response = await route.fetch({ url: origin + url.pathname + url.search })
          await route.fulfill({ response })
        })
        await context.addInitScript(() => {
          window.__fincoCspViolations = []
          document.addEventListener('securitypolicyviolation', event => window.__fincoCspViolations.push(event.effectiveDirective))
        })
        const page = await context.newPage()
        const errors = []
        page.on('pageerror', error => errors.push(error.message))
        const pending = new Set()
        page.on('request', request => pending.add(new URL(request.url()).pathname))
        page.on('requestfinished', request => pending.delete(new URL(request.url()).pathname))
        page.on('requestfailed', request => pending.delete(new URL(request.url()).pathname))
        // Use the same deterministic network boundary as the public phase.
        // Live provider verification has its own explicitly configured origin.
        if (browserOrigin === origin) await context.route('**/*', route => new URL(route.request().url()).origin === origin ? route.continue() : route.abort())
        await phase('login-navigation', { width, reducedMotion })
        let navigationError = null
        try {
          // Navigation commit proves the server response; visible form controls
          // prove usability. A browser lifecycle event alone is neither proof.
          const response = await page.goto(browserOrigin + '/login', { waitUntil:'commit' }).catch(error => { navigationError=error.message; throw error })
          assert.equal(response?.status(),200,'Cold login document must succeed')
          await page.locator('input[type=email]').waitFor()
          if(process.env.FINCO_CONFIGURED_CLERK_CHECK!=='true')await page.locator('input[type=password]').waitFor()
          assert.equal(new URL(page.url()).pathname,'/login')
        } catch (error) {
          const diagnostics={width,reducedMotion,url:page.url(),navigationError,pending:[...pending],errors,emailVisible:await page.locator('input[type=email]').isVisible().catch(()=>false),passwordVisible:await page.locator('input[type=password]').isVisible().catch(()=>false),nginxError:(await readFile(path.join(work,'error.log'),'utf8')).slice(-6000)}
          console.log('Login readiness diagnostics',JSON.stringify(diagnostics))
          await writeFile(path.join(output, 'login-readiness-failure.json'), JSON.stringify(diagnostics,null,2))
          throw error
        }
        if (process.env.FINCO_CONFIGURED_CLERK_CHECK === 'true') assert.equal(await page.getByRole('button', { name: /Google/ }).count(), 1, 'Configured Google login missing')
        await phase('login-fonts', { width, reducedMotion })
        await page.evaluate(() => document.fonts.ready)
        await page.waitForTimeout(800)
        assert.equal(await page.locator('main').count(), 1)
        assert.equal(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth + 1), false)
        assert.deepEqual(errors, [])
        if (process.env.FINCO_STRICT_CSP_MODE === 'enforce') assert.deepEqual(await page.evaluate(() => window.__fincoCspViolations), [], 'Strict CSP blocked an app resource')
        await phase('login-accessibility', { width, reducedMotion })
        const axe = await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa', 'wcag21aa']).analyze()
        assert.deepEqual(axe.violations.map(item => ({ id: item.id, impact: item.impact, targets: item.nodes.map(node => node.target) })), [])
        const resources = await page.evaluate(() => performance.getEntriesByType('resource').map(resource => ({ name: new URL(resource.name).pathname, transfer: resource.transferSize, decoded: resource.decodedBodySize })))
        assert(!resources.some(resource => /app-layout|CartesianChart|chat-panel|pt-BR/.test(resource.name)), 'Signed-out page loaded a private/heavy module')
        if (width < 1024) assert(!resources.some(resource => /auth-brand-panel/.test(resource.name)), 'Hidden desktop decoration loaded on mobile')
        await phase('login-screenshot', { width, reducedMotion })
        if (reducedMotion === 'no-preference' && [390, 1440].includes(width)) await page.screenshot({ path: path.join(output, `${width}.png`), fullPage: true })
        await phase('login-keyboard', { width, reducedMotion })
        await page.locator('input[type=email]').focus()
        // Preserve the actual visible order: email, verification link, recovery
        // link, password. Do not change product navigation to satisfy a test.
        for (const selector of ['a[href="/request-verification"]', 'a[href="/forgot-password"]', 'input[type=password]']) {
          await page.keyboard.press('Tab')
          assert.equal(await page.locator(selector).evaluate(element => document.activeElement === element), true, `Tab target: ${selector}`)
        }
        results.push({ width, reducedMotion, axeViolations: axe.violations.length, decodedBytes: resources.reduce((total, resource) => total + resource.decoded, 0), jsRequests: resources.filter(resource => resource.name.endsWith('.js')).length, resources })
        await phase('login-context-close', { width, reducedMotion })
        await context.close()
      }
    }
  }
  // Optional local lab measurement; configuration API above is synthetic.
  if (process.env.PERF_TOOLS_ROOT) {
    const { default: lighthouse } = await import(path.join(process.env.PERF_TOOLS_ROOT, 'node_modules/lighthouse/core/index.js'))
    const { launch } = await import(path.join(process.env.PERF_TOOLS_ROOT, 'node_modules/chrome-launcher/dist/index.js'))
    // Explicit loopback debug port also supports the pinned Chromium 141,
    // whose stderr format predates launcher's dynamic-port discovery.
    const debugProbe = http.createServer()
    await new Promise(resolve => debugProbe.listen(0, '127.0.0.1', resolve))
    const debugPort = debugProbe.address().port
    await new Promise(resolve => debugProbe.close(resolve))
    const chrome = await launch({ port: debugPort, chromePath: process.env.LIGHTHOUSE_CHROME_PATH || chromium.executablePath(), chromeFlags: ['--headless', '--no-sandbox', '--disable-dev-shm-usage'] })
    try {
      const { lhr } = await lighthouse(origin + '/login', { port: chrome.port, output: 'json', logLevel: 'error', onlyCategories: ['performance', 'accessibility', 'best-practices', 'seo'] })
      await writeFile(path.join(output, 'lighthouse.json'), JSON.stringify(lhr))
      const metrics = Object.fromEntries(['first-contentful-paint', 'largest-contentful-paint', 'total-blocking-time', 'cumulative-layout-shift', 'speed-index', 'total-byte-weight'].map(id => [id, lhr.audits[id].numericValue]))
      const summary = { mode: 'local nginx production template, synthetic public config, no real login', scores: Object.fromEntries(Object.entries(lhr.categories).map(([key, category]) => [key, category.score])), metrics }
      await writeFile(path.join(output, 'lab-summary.json'), JSON.stringify(summary, null, 2))
      console.log(JSON.stringify(summary))
    } finally { await chrome.kill() }
  }
  await phase('complete', { cases: results.length })
  await writeFile(path.join(output, 'browser.json'), JSON.stringify(results, null, 2))
  console.log(JSON.stringify({ mode: 'synthetic public config', nginxHeaders: labOnly ? 'not run (lab-only mode)' : 'passed', browserCases: results.length, cases: results.map(({ resources: _resources, ...result }) => result) }))
} finally {
  await browser?.close()
  nginx.kill('SIGTERM')
  await new Promise(resolve => backend.close(resolve))
}
