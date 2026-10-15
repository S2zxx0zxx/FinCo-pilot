/** Inspect final prerendered bytes. No network, credentials or finance APIs. */
import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
import { getMarketingConfig, PUBLIC_PAGES, marketingUrl, marketingSocialImage, RESTRICTED_CRAWLERS } from '../lib/marketing.ts'

const { origin, indexable, basePath } = getMarketingConfig()
const titles = new Set()
const exported = basePath !== ''
const buildRoot = exported ? '../.next-export/' : '../.next/server/app/'
for (const page of PUBLIC_PAGES) {
  const file = page.path === '/' ? 'index' : page.path.slice(1)
  const output = exported ? (page.path === '/' ? 'index.html' : `${file}/index.html`) : `${file}.html`
  const html = await readFile(new URL(buildRoot + output, import.meta.url), 'utf8')
  const title = html.match(/<title>(.*?)<\/title>/s)?.[1]
  assert.ok(title && !titles.has(title), `${page.path}: unique title`)
  titles.add(title)
  assert.equal((html.match(/<h1\b/g) || []).length, 1, `${page.path}: one initial H1`)
  const canonical = html.match(/<link rel="canonical" href="([^"]+)"/)?.[1]
  assert.equal(canonical && new URL(canonical).href, marketingUrl(page.path), `${page.path}: canonical`)
  const robots = html.match(/<meta name="robots" content="([^"]+)"/)?.[1]
  assert.ok(robots, `${page.path}: robots metadata`)
  assert.equal(robots.includes('noindex'), !indexable)
  assert.ok(html.includes(`property="og:image" content="${marketingSocialImage()}"`), `${page.path}: social image`)
  const graphs = [...html.matchAll(/<script type="application\/ld\+json">(.*?)<\/script>/gs)].map(match => JSON.parse(match[1]))
  assert.equal(graphs.filter(graph => graph['@type'] === 'WebSite').length, 1)
  assert.ok(!JSON.stringify(graphs).match(/aggregateRating|reviewCount|priceCurrency|taxID/))
  if (page.path !== '/') {
    const trail = graphs.find(graph => graph['@type'] === 'BreadcrumbList')
    assert.equal(trail?.itemListElement.at(-1).item, marketingUrl(page.path))
    assert.ok(html.includes('aria-label="Breadcrumb"'))
    assert.ok(html.includes('Go to sign up'))
  }
}
const sitemap = await readFile(new URL(buildRoot + (exported ? 'sitemap.xml' : 'sitemap.xml.body'), import.meta.url), 'utf8')
assert.match(sitemap, /<urlset xmlns="http:\/\/www.sitemaps.org\/schemas\/sitemap\/0.9">/)
const locations = [...sitemap.matchAll(/<loc>(.*?)<\/loc>/g)].map(match => match[1])
assert.deepEqual(locations, indexable ? PUBLIC_PAGES.map(page => marketingUrl(page.path)) : [])
assert.ok(!sitemap.includes('<lastmod>'), 'No invented update dates')
const robotsText = await readFile(new URL(buildRoot + (exported ? 'robots.txt' : 'robots.txt.body'), import.meta.url), 'utf8')
assert.match(robotsText, /User-Agent: \*/)
if (indexable) {
  assert.ok(robotsText.includes(`Sitemap: ${origin}${basePath}/sitemap.xml`))
  for (const agent of RESTRICTED_CRAWLERS) assert.ok(robotsText.includes(`User-Agent: ${agent}\n`), agent)
} else {
  assert.match(robotsText, /Disallow: \/\n/)
  assert.ok(!robotsText.includes('Sitemap:'))
}
console.log(JSON.stringify({ mode: indexable ? 'explicit-production-fixture' : 'excluded-preview', origin, basePath, pages: PUBLIC_PAGES.length, sitemapUrls: locations.length, result: 'PASS' }))
