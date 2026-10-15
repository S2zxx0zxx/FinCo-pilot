import assert from 'node:assert/strict'
import { mkdir, writeFile } from 'node:fs/promises'
import { chromium, firefox, webkit } from 'playwright'
import axe from 'axe-core'

const origin = process.env.LANDING_TEST_URL || 'http://127.0.0.1:3100'
assert.ok(['localhost', '127.0.0.1'].includes(new URL(origin).hostname), 'Use an isolated local build')
const browserType = { chromium, firefox, webkit }[process.env.LANDING_BROWSER || 'chromium']
assert.ok(browserType)
const browser = await browserType.launch({ headless: true, args: browserType === chromium ? ['--no-sandbox'] : [] })
const paths = ['/features', '/how-it-works', '/guides/import-transactions']
const report = { engine: browserType.name(), pages: [], scope: 'Isolated marketing; no provider or authenticated app acceptance' }
await mkdir(new URL('../test-artifacts/', import.meta.url), { recursive: true })
try {
  for (const width of [320,390,768,1440]) {
    const context = await browser.newContext({ viewport: { width, height: 900 }, reducedMotion: 'reduce' })
    for (const path of paths) {
      const page = await context.newPage()
      const external = []; const errors = []
      page.on('pageerror', error => errors.push(error.message))
      page.on('request', request => { if (new URL(request.url()).origin !== new URL(origin).origin) external.push(request.url()) })
      assert.equal((await page.goto(origin + path, { waitUntil: 'networkidle' })).status(), 200)
      assert.equal(await page.locator('h1').count(), 1)
      assert.ok(await page.locator('h1').isVisible())
      assert.equal(await page.getByRole('main').count(), 1)
      assert.equal(await page.getByRole('navigation', { name: 'Breadcrumb', exact: true }).count(), 1)
      assert.ok(await page.getByRole('link', { name: 'Go to sign up', exact: true }).count())
      assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1), `${path}: overflow at ${width}`)
      await page.keyboard.press('Tab')
      assert.equal(await page.evaluate(() => document.activeElement.textContent), 'Skip to content')
      await page.keyboard.press('Enter')
      await page.addScriptTag({ content: axe.source })
      const violations = await page.evaluate(async () => (await window.axe.run(document, {
        runOnly: { type: 'tag', values: ['wcag2a','wcag2aa','wcag21aa','wcag22aa'] },
      })).violations.map(value => ({ id: value.id, impact: value.impact, nodes: value.nodes.map(node => node.target) })))
      assert.deepEqual(violations, [], `${path}: accessibility at ${width}`)
      assert.deepEqual(errors, [])
      assert.deepEqual(external, [], 'Marketing must not request finance APIs or external trackers')
      if (width === 390 || width === 1440) await page.screenshot({ path: new URL(`../test-artifacts/discovery-${browserType.name()}-${path.split('/').at(-1)}-${width}.png`, import.meta.url).pathname, fullPage: true })
      report.pages.push({ path, width, accessibilityViolations: 0, externalRequests: 0 })
      await page.close()
    }
    await context.close()
    console.log(`PASS: ${browserType.name()} documentation at ${width}px`)
  }
  const context = await browser.newContext({ javaScriptEnabled: false })
  for (const path of paths) {
    const page = await context.newPage()
    await page.goto(origin + path)
    assert.ok(await page.locator('h1').isVisible())
    assert.ok((await page.getByRole('main').innerText()).length > 800)
    await page.close()
  }
  await context.close()
  await writeFile(new URL(`../test-artifacts/discovery-${browserType.name()}.json`, import.meta.url), JSON.stringify(report, null, 2))
  console.log(JSON.stringify({ engine: report.engine, viewportPageChecks: report.pages.length, noJsPages: paths.length, result: 'PASS' }))
} finally { await browser.close() }
