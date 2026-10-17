import test from 'node:test'
import assert from 'node:assert/strict'
import { getMarketingConfig, marketingUrl, sitemapEntries, serializeJsonLd, marketingSocialImage, websiteSchema, RESTRICTED_CRAWLERS } from '../lib/marketing.ts'

const production = { VERCEL_ENV: 'production', NEXT_PUBLIC_MARKETING_INDEXABLE: 'true', NEXT_PUBLIC_MARKETING_URL: 'https://discover.fincopilot.app' }

test('publication requires production AND opt-in AND explicit owned canonical origin', () => {
  assert.equal(getMarketingConfig({}).indexable, false)
  assert.equal(getMarketingConfig({ ...production, VERCEL_ENV: 'preview' }).indexable, false)
  assert.equal(getMarketingConfig({ ...production, NEXT_PUBLIC_MARKETING_INDEXABLE: 'false' }).indexable, false)
  assert.throws(() => getMarketingConfig({ VERCEL_ENV: 'production', NEXT_PUBLIC_MARKETING_INDEXABLE: 'true' }))
  assert.equal(getMarketingConfig(production).origin, 'https://discover.fincopilot.app')
  for (const url of ['http://fincopilot.app','https://evil.test','https://fincopilot.app.evil.test',
    'https://user:password@fincopilot.app','https://fincopilot.app/?token=x','https://fincopilot.app/#x',
    'https://fincopilot.app/path','https://fincopilot.app:444','https://branch.vercel.app']) {
    assert.throws(() => getMarketingConfig({ ...production, NEXT_PUBLIC_MARKETING_URL: url }), url)
  }
})

test('sitemap is empty in excluded builds; only fixed canonical public pages qualify', () => {
  assert.deepEqual(sitemapEntries({}), [])
  assert.deepEqual(sitemapEntries({ ...production, VERCEL_ENV: 'preview' }), [])
  const entries = sitemapEntries(production)
  assert.equal(entries.length, 4)
  assert.equal(new Set(entries.map(entry => entry.url)).size, 4)
  for (const entry of entries) {
    assert.equal(new URL(entry.url).origin, production.NEXT_PUBLIC_MARKETING_URL)
    assert.ok(!('lastModified' in entry), 'Do not fabricate freshness')
    assert.doesNotMatch(entry.url, /login|register|api\/|oauth|pricing|privacy|terms|i\//)
  }
  for (const path of ['/login','/accounts','/i/secret','https://evil.test/','/?token=x']) {
    assert.throws(() => marketingUrl(path, production))
  }
})

test('JSON-LD escapes script termination and does not invent commercial claims', () => {
  const value = { name: '</script><script>bad()</script>' }
  const output = serializeJsonLd(value)
  assert.ok(!output.includes('<'))
  assert.deepEqual(JSON.parse(output), value)
})

test('restricted training and user agents retain the observed policy independently of search', () => {
  assert.ok(RESTRICTED_CRAWLERS.includes('GPTBot'))
  assert.ok(RESTRICTED_CRAWLERS.includes('ChatGPT-User'))
  assert.ok(!RESTRICTED_CRAWLERS.includes('OAI-SearchBot'))
})


test('same-origin static export uses actual welcome paths for canonical, sitemap, schema and social image', () => {
  const exported = { ...production, NEXT_PUBLIC_MARKETING_URL: 'https://fincopilot.app', FINCO_EXPORT_MARKETING: 'true', FINCO_MARKETING_PUBLICATION_APPROVED: 'true' }
  assert.equal(marketingUrl('/', exported), 'https://fincopilot.app/welcome/')
  assert.equal(marketingUrl('/features', exported), 'https://fincopilot.app/welcome/features/')
  assert.equal(marketingUrl('/guides/import-transactions', exported), 'https://fincopilot.app/welcome/guides/import-transactions/')
  assert.equal(marketingSocialImage(exported), 'https://fincopilot.app/welcome/social-card.png')
  assert.equal(websiteSchema(exported).url, marketingUrl('/', exported))
  assert.equal(websiteSchema(exported)['@id'], marketingUrl('/', exported) + '#website')
  for (const entry of sitemapEntries(exported)) assert.ok(new URL(entry.url).pathname.startsWith('/welcome/'))
  assert.deepEqual(sitemapEntries({ ...exported, VERCEL_ENV: 'preview' }), [])
  assert.equal(marketingUrl('/features', production), 'https://discover.fincopilot.app/features')
  assert.equal(marketingSocialImage(production), 'https://discover.fincopilot.app/social-card.png')
})
