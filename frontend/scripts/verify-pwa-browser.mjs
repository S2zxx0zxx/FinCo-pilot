import assert from 'node:assert/strict'
import { createServer } from 'node:http'
import { readFile } from 'node:fs/promises'
import path from 'node:path'
import { chromium } from 'playwright'

// Real Chromium + built app + actual service worker/cache, synthetic API only.
// No live accounts, install claims or production infrastructure changes.
const dist = path.resolve('dist')
const shell = await readFile(path.join(dist, 'index.html'))
const worker = await readFile(path.join(dist, 'sw.js'), 'utf8')
assert.match(worker, /const VERSION = 'finco-pwa-v5-[a-f0-9]{20}'/)
let release = 1
let badShell = false
let writes = 0
const mime = { '.html': 'text/html', '.js': 'text/javascript', '.css': 'text/css', '.json': 'application/json', '.webmanifest': 'application/manifest+json', '.svg': 'image/svg+xml', '.png': 'image/png', '.woff2': 'font/woff2' }
const server = createServer(async (req, res) => {
  const url = new URL(req.url, 'http://localhost')
  res.setHeader('Cache-Control', 'no-store')
  if (url.pathname === '/sw.js') {
    res.setHeader('Content-Type', 'text/javascript')
    res.end(release === 1 ? worker : worker.replace(/(const VERSION = '[^']+)'/, '$1-browser-update\''))
    return
  }
  if (url.pathname.startsWith('/api') || url.pathname.startsWith('/mcp')) {
    if (req.method === 'POST') writes++
    res.setHeader('Content-Type', 'application/json')
    const fixture = url.pathname === '/api/auth/oidc/config'
      ? { enabled: false, provider_name: 'Synthetic', local_auth_enabled: true }
      : url.pathname === '/api/setup/status'
        ? { has_users: true, setup_available: false }
        : { synthetic: true, secret: 'synthetic-financial-marker', writes }
    res.end(JSON.stringify(fixture))
    return
  }
  if (url.pathname === '/poison' || (badShell && url.pathname === '/')) {
    res.setHeader('Content-Type', 'text/html')
    res.end('<!doctype html><title>Proxy sign-in</title><p>synthetic-private-document</p>')
    return
  }
  if (url.pathname === '/reset-password' || url.pathname === '/verify-email') {
    res.setHeader('Content-Type', 'text/html')
    res.end('<!doctype html><p>synthetic-recovery-marker</p>')
    return
  }
  try {
    const file = path.resolve(dist, '.' + url.pathname)
    if (!file.startsWith(dist + path.sep)) throw new Error('Not a public file')
    const bytes = await readFile(file)
    res.setHeader('Content-Type', mime[path.extname(file)] || 'application/octet-stream')
    if (url.pathname.startsWith('/static/')) res.setHeader('Cache-Control', 'public,max-age=31536000,immutable')
    res.end(bytes)
  } catch {
    res.setHeader('Content-Type', 'text/html')
    res.end(shell)
  }
})
await new Promise(resolve => server.listen(0, '127.0.0.1', resolve))
const base = `http://127.0.0.1:${server.address().port}`
const browser = await chromium.launch({ headless: true })
const results = []
async function eventually(check) {
  const deadline = Date.now() + 15000
  while (Date.now() < deadline) {
    if (await check()) return
    await new Promise(resolve => setTimeout(resolve, 50))
  }
  throw new Error('Timed out waiting for browser acceptance state')
}
async function cached(page) {
  return page.evaluate(async () => {
    const output = []
    for (const name of await caches.keys()) {
      const c = await caches.open(name)
      for (const req of await c.keys()) {
        const response = await c.match(req)
        output.push({ name, url: req.url, responseUrl: response.url, text: (response.headers.get('content-type') || '').includes('text') ? await response.text() : '' })
      }
    }
    return output
  })
}
try {
  for (const device of [
    { name: 'desktop Chromium', viewport: { width: 1440, height: 900 } },
    { name: 'mobile Chromium emulation', viewport: { width: 393, height: 852 }, isMobile: true, hasTouch: true },
  ]) {
    const context = await browser.newContext({ ...device, name: undefined, reducedMotion: 'reduce' })
    const page = await context.newPage()
    await page.goto(base + '/')
    await page.waitForFunction(() => navigator.serviceWorker.controller !== null)
    await page.reload()
    await page.waitForFunction(() => document.querySelector('#root')?.childElementCount > 0)
    await page.locator('input[type="password"]').first().waitFor()
    const manifest = await page.evaluate(async () => (await fetch('/manifest.webmanifest')).json())
    assert.equal(manifest.display, 'standalone')
    assert.equal(manifest.scope, '/')
    for (const icon of [...manifest.icons, { src: '/apple-touch-icon.png', sizes: '180x180' }]) {
      const dimensions = await page.evaluate(async src => {
        const blob = await (await fetch(src)).blob()
        const image = await createImageBitmap(blob)
        return `${image.width}x${image.height}`
      }, icon.src)
      assert.equal(dimensions, icon.sizes)
    }
    await page.evaluate(async () => {
      await fetch('/api/financial-data')
      await fetch('/api')
      await fetch('/mcp')
      await fetch('/api/transaction', { method: 'POST', body: 'synthetic' })
    })
    assert.equal(writes, results.length + 1)
    await page.goto(base + '/reset-password?token=synthetic-token')
    await page.goto(base + '/verify-email?token=synthetic-token')
    await page.goto(base + '/poison')
    const inventory = await cached(page)
    assert(inventory.some(x => new URL(x.url).pathname === '/'))
    assert(!inventory.some(x => /synthetic-private-document|synthetic-recovery-marker|synthetic-financial-marker/.test(x.text)))
    assert(!inventory.some(x => /\/api(?:\/|$)|\/mcp(?:\/|$)|token=/.test(x.url) || /token=/.test(x.responseUrl)))
    await context.setOffline(true)
    await page.goto(base + '/transactions')
    await page.waitForFunction(() => document.querySelector('#root')?.childElementCount > 0)
    assert.match(await page.locator('body').innerText(), /offline/i)
    await context.setOffline(false)
    // Hold one stable controlled document while exercising worker lifecycle;
    // application startup update checks are verified separately by UI tests.
    await page.goto(base + '/poison')
    await page.waitForFunction(() => navigator.serviceWorker.controller !== null)
    const before = await page.evaluate(async () => (await caches.keys()).sort())
    release = 2
    await page.evaluate(async () => (await navigator.serviceWorker.getRegistration()).update())
    await eventually(() => page.evaluate(async () => {
      const waiting = (await navigator.serviceWorker.getRegistration())?.waiting
      if (waiting) window.fincoTestWaitingWorker = waiting
      return Boolean(waiting)
    }))
    const waitingCaches = await page.evaluate(async () => (await caches.keys()).sort())
    assert(before.every(x => waitingCaches.includes(x)), 'Waiting release must preserve active caches')
    assert(waitingCaches.length > before.length, 'Waiting release must have isolated caches')
    await page.evaluate(async () => {
      const waiting = window.fincoTestWaitingWorker
      if (!waiting || waiting.state !== 'installed') throw new Error(`Worker left waiting without acceptance: ${waiting?.state}`)
      await new Promise(resolve => {
        navigator.serviceWorker.addEventListener('controllerchange', resolve, { once: true })
        waiting.postMessage({ type: 'SKIP_WAITING' })
      })
    })
    await eventually(() => page.evaluate(async () => (await caches.keys()).every(x => x.includes('browser-update'))))
    await context.setOffline(true)
    await page.goto(base + '/reports')
    await page.waitForFunction(() => document.querySelector('#root')?.childElementCount > 0)
    assert.match(await page.locator('body').innerText(), /offline/i)
    assert.equal(writes, results.length + 1, 'Offline/reconnect/update must not replay financial POSTs')
    results.push({ browser: device.name, manifestIcons: 'PASS', privacy: 'PASS', offlineDeepLinks: 'PASS', waitingUpdateIsolation: 'PASS', acceptedUpdate: 'PASS' })
    await context.close()
    release = 1
  }
  // A 200 proxy login document must not become a newly installed shell.
  badShell = true
  const context = await browser.newContext()
  const page = await context.newPage()
  await page.goto(base + '/')
  await page.evaluate(() => navigator.serviceWorker.register('/sw.js'))
  await eventually(() => page.evaluate(async () => !(await navigator.serviceWorker.getRegistration())?.installing))
  assert(!(await cached(page)).some(x => x.text.includes('synthetic-private-document')))
  assert.equal(await page.evaluate(() => Boolean(navigator.serviceWorker.controller)), false)
  await context.close()
  console.log(JSON.stringify({ results, rejectedProxyShell: 'PASS', scope: 'real desktop Chromium and mobile emulation; synthetic API; physical Android/iOS and live HTTPS pending' }, null, 2))
} finally {
  await browser.close()
  await new Promise(resolve => server.close(resolve))
}
