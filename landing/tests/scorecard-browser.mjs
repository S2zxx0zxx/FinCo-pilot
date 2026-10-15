import assert from 'node:assert/strict'
import { chromium } from 'playwright'
import axe from 'axe-core'

const browser = await chromium.launch({ headless: true, args: ['--no-sandbox'] })
try {
  for (const width of [390,1440]) {
    const page = await browser.newPage({ viewport: { width, height: 900 } })
    const external = []
    page.on('request', request => { if (/^https?:/.test(request.url())) external.push(request.url()) })
    await page.goto(new URL('../../docs/growth/dashboard.html', import.meta.url).href)
    assert.equal(await page.locator('#metrics tr').count(), 14)
    assert.equal(await page.locator('#metrics td').filter({ hasText: /^Unknown$/ }).count(), 14)
    const report = { schema_version: 1, period: { start: '2026-10-01', end: '2026-10-14' },
      metrics: { google_clicks: { value: 5, status: 'export-derived' } } }
    await page.locator('#report').setInputFiles({ name: 'synthetic-report.json', mimeType: 'application/json', buffer: Buffer.from(JSON.stringify(report)) })
    await page.getByText('Sanitized report loaded locally.', { exact: false }).waitFor()
    assert.ok((await page.locator('#metrics tr').first().innerText()).includes('5'))
    await page.locator('#report').setInputFiles({ name: 'invalid-report.json', mimeType: 'application/json',
      buffer: Buffer.from(JSON.stringify({ schema_version: 1, metrics: { google_clicks: { value: '<img src=https://evil.test>', status: 'export-derived' } } })) })
    await page.getByText('Report rejected.', { exact: false }).waitFor()
    assert.equal(await page.locator('#metrics td').filter({ hasText: /^Unknown$/ }).count(), 14)
    await page.getByRole('button', { name: 'Clear report' }).click()
    await page.addScriptTag({ content: axe.source })
    const violations = await page.evaluate(async () => (await window.axe.run(document, {
      runOnly: { type: 'tag', values: ['wcag2a','wcag2aa','wcag21aa','wcag22aa'] },
    })).violations.map(value => value.id))
    assert.deepEqual(violations, [])
    assert.deepEqual(external, [])
    assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1))
    await page.close()
  }
  console.log('PASS: local scorecard import/reset, hostile input rejection, unknowns, responsive accessibility, zero network requests')
} finally { await browser.close() }
