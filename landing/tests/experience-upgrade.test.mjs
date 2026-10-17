import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { execFileSync } from 'node:child_process'
import { createHash } from 'node:crypto'
import {
  spendingRemainder,
  spendingScenarios,
} from '../lib/spending-example.ts'
const read = (path) =>
  readFileSync(new URL('../' + path, import.meta.url), 'utf8')
test('spending illustration handles presets, zero, shortfall and invalid reserves', () => {
  assert.deepEqual(
    spendingScenarios.map((s) => spendingRemainder(s.bills, s.buffer, s.goal)),
    [25000, 9000, 10000],
  )
  assert.equal(spendingRemainder(22000, 35000, 5000), 0)
  assert.equal(spendingRemainder(22000, 40000, 5000), -5000)
  for (const bad of [NaN, Infinity, -1, 62001])
    assert.equal(spendingRemainder(22000, bad, 5000), null)
  assert.equal(spendingRemainder(0, 0, 0), 62000)
})
test('standard-plan preview stays in sync with both authoritative catalogs', () => {
  execFileSync(process.execPath, ['scripts/marketing-content.mjs', '--check'], {
    cwd: new URL('../', import.meta.url),
  })
  const catalog = JSON.parse(read('lib/standard-plans.json'))
  assert.deepEqual(
    catalog.prices.map((p) => [p.plan, p.interval, p.amount_minor]),
    [
      ['free', 'none', 0],
      ['pro', 'monthly', 9900],
      ['pro', 'annual', 99900],
      ['max', 'monthly', 34900],
    ],
  )
  assert.match(read('components/plan-preview.tsx'), /No standard annual option/)
})
test('all six original application specimens have traceable responsive assets', () => {
  for (const path of [
    'docs/PRODUCT_CAPTURE_PROVENANCE.json',
    'docs/PRODUCT_CAPTURE_EXTENDED.json',
  ]) {
    const provenance = JSON.parse(read(path))
    assert.match(provenance.data, /Synthetic/)
    for (const capture of provenance.captures) {
      const file = readFileSync(
        new URL(
          '../public/product/' + (capture.webp ?? capture.file),
          import.meta.url,
        ),
      )
      assert.equal(
        createHash('sha256').update(file).digest('hex'),
        capture.webp_sha256 ?? capture.sha256,
      )
      assert.deepEqual(capture.pageErrors, [])
    }
  }
  const extended = JSON.parse(read('docs/PRODUCT_CAPTURE_EXTENDED.json'))
  assert.equal(extended.captures.length, 8)
  assert.deepEqual(
    [...new Set(extended.captures.map((c) => c.name))],
    ['budgets', 'goals', 'recurring', 'reports'],
  )
})
