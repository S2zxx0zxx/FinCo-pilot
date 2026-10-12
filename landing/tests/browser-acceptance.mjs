import assert from 'node:assert/strict'
import { mkdir } from 'node:fs/promises'
import { chromium } from 'playwright'

const origin = process.env.LANDING_TEST_URL || 'http://127.0.0.1:3100'
const screenshots = new URL('../test-artifacts/', import.meta.url)
await mkdir(screenshots, { recursive: true })
const browser = await chromium.launch({ headless: true, args: ['--no-sandbox'] })
const widths = [320, 375, 390, 768, 1024, 1440]
const errors = []
const report = []

try {
  for (const width of widths) {
    const context = await browser.newContext({
      viewport: { width, height: width < 500 ? 812 : 900 },
      deviceScaleFactor: 1, isMobile: width < 500, hasTouch: width < 500,
      reducedMotion: width === 375 ? 'reduce' : 'no-preference',
    })
    const page = await context.newPage()
    const pageErrors = []
    page.on('pageerror', err => pageErrors.push(err.message))
    const response = await page.goto(origin + '/', { waitUntil: 'networkidle', timeout: 45000 })
    assert.equal(response?.status(), 200, width + ': homepage HTTP status')
    assert.equal(await page.locator('h1').count(), 1, width + ': exactly one H1')
    assert.match(await page.locator('h1').getAttribute('aria-label') || '', /Money makes more sense together/)
    const dimensions = await page.evaluate(() => ({
      viewport: window.innerWidth,
      htmlWidth: document.documentElement.scrollWidth,
      bodyWidth: document.body.scrollWidth,
      rootWidth: document.querySelector('.marketing-page')?.scrollWidth,
    }))
    assert.ok(dimensions.htmlWidth <= dimensions.viewport + 2,
      width + ': overflow detected: ' + JSON.stringify(dimensions))
    for (const path of ['/login', '/register', '/pricing', '/privacy', '/terms', '/support']) {
      const loc = page.locator('a[href="https://fincopilot.app' + path + '"]')
      assert.ok(await loc.count() >= 1, width + ': missing real product route ' + path)
    }
    assert.ok(await page.getByText('Illustrative interface').count() >= 1, width + ': missing sample disclaimer')
    const tabs = page.getByRole('tablist', { name: 'Explore sample views' })
    await tabs.getByRole('tab', { name: 'Budgets' }).click()
    assert.match(await page.locator('#sample-panel').innerText(), /₹24,800/)
    await tabs.getByRole('tab', { name: 'Activity' }).click()
    assert.match(await page.locator('#sample-panel').innerText(), /18 items/)
    await tabs.getByRole('tab', { name: 'Overview' }).click()
    assert.match(await page.locator('#sample-panel').innerText(), /₹1,84,250/)
    const question = page.getByRole('button', { name: 'Do I have to connect a bank account?' })
    await question.click()
    await page.getByText('FinCo-Pilot supports managing financial accounts and transactions manually.', { exact: false }).waitFor({ timeout: 5000 })
    if (width <= 920) {
      const menu = page.getByRole('button', { name: 'Open navigation' })
      await menu.click()
      assert.equal(await page.getByRole('button', { name: 'Close navigation' }).getAttribute('aria-expanded'), 'true')
      await page.getByRole('navigation', { name: 'Mobile navigation' }).getByRole('link', { name: 'Why FinCo' }).click()
      assert.equal(await page.getByRole('button', { name: 'Open navigation' }).getAttribute('aria-expanded'), 'false')
    } else {
      assert.ok(await page.getByRole('navigation', { name: 'Primary navigation' }).isVisible())
    }
    if (width === 375) {
      const scroll = await page.evaluate(() => getComputedStyle(document.documentElement).scrollBehavior)
      assert.equal(scroll, 'auto', 'reduced motion must disable smooth scroll')
    }
    if (width === 390 || width === 1440) {
      await page.screenshot({ path: new URL(width + '-full.png', screenshots).pathname, fullPage: true, animations: 'disabled' })
    }
    assert.deepEqual(pageErrors, [], width + ': JavaScript page errors')
    report.push({ width, status: 'passed', ...dimensions })
    await context.close()
  }
  const keyboard = await browser.newContext({ viewport: { width: 1440, height: 900 } })
  const p = await keyboard.newPage()
  await p.goto(origin, {waitUntil:'domcontentloaded'})
  await p.keyboard.press('Tab')
  assert.equal(await p.evaluate(() => document.activeElement?.textContent?.trim()), 'Skip to content')
  await p.keyboard.press('Enter')
  assert.equal(new URL(p.url()).hash, '#main-content')
  await keyboard.close()
  console.log('PASS: browser responsive + CTA + tabs + accordion + menu + reduced motion + keyboard')
  console.log(JSON.stringify({ testedWidths: report, screenshots: ['390-full.png','1440-full.png'] }, null, 2))
} catch(err) {
  errors.push(String(err))
  console.error('FAIL: landing browser acceptance', err)
  throw err
} finally {
  await browser.close()
}
