/** Production entry regression gate. No network, credentials or private data. */
import assert from 'node:assert/strict'
import { readFile, readdir } from 'node:fs/promises'
import { createHash } from 'node:crypto'
import { gzipSync } from 'node:zlib'
import path from 'node:path'
import { marketingPublicationEnv } from './marketing-publication-policy.mjs'

const dist = path.resolve('dist')
const html = await readFile(path.join(dist, 'index.html'), 'utf8')
assert(!html.includes('/@vite/client') && !html.includes('/src/main.tsx'), 'Development server output must never ship')
assert.match(html, /name="description"/, 'Description missing')
assert.match(html, /<meta name="robots" content="noindex"\s*\/>/, 'Private app shell must remain excluded from indexing')
const structured = JSON.parse(html.match(/<script type="application\/ld\+json">(.*?)<\/script>/s)?.[1] || '{}')
assert.equal(structured['@type'], 'WebApplication')
assert.equal(structured.name, 'FinCo-Pilot')

// Independently check delivered entry bytes, not a temporary bundler chunk.
for (const match of html.matchAll(/<(?:script|link)[^>]+(?:src|href)="([^"]+)"[^>]+integrity="(sha256-[^"]+)"/g)) {
  const code = await readFile(path.join(dist, match[1].slice(1)))
  assert.equal(match[2], `sha256-${createHash('sha256').update(code).digest('base64')}`, 'Stale entry SRI')
}
assert.match(html, /integrity="sha256-/)

// Sign-in waterfall regression: build-derived, origin-local module hints must
// refer to real chunks and the exact final JS bytes. Never pull Clerk modules
// on public marketing, recovery, or authenticated route navigation.
const hintSource = html.match(/const h=(\{[^;]+\});const p=location.pathname/)
assert(hintSource, 'Route-specific public login hints missing')
const hint = JSON.parse(hintSource[1])
for (const [chunkKey, sriKey] of [
  ['login', 'loginIntegrity'],
  ['clerkLogin', 'clerkLoginIntegrity'],
  ['clerkAdapter', 'clerkAdapterIntegrity'],
]) {
  const moduleUrl = hint[chunkKey]
  if (chunkKey !== 'login' && moduleUrl === null) continue
  assert.match(moduleUrl, /^\/static\/[\w.-]+\.js$/, `Invalid ${chunkKey} module path`)
  const bytes = await readFile(path.join(dist, moduleUrl.slice(1)))
  assert.equal(hint[sriKey], `sha256-${createHash('sha256').update(bytes).digest('base64')}`,
    `Missing/stale ${chunkKey} hint SRI`)
}
assert.equal(Boolean(hint.clerkLogin), Boolean(hint.clerkAdapter),
  'Clerk sign-in modules must be hinted together')
assert(html.includes("if((p==='/login'||p==='/sign-in')&&h.clerkLogin&&h.clerkAdapter)"),
  'Clerk module preload must remain restricted to sign-in routes')
const policy = JSON.parse(await readFile('node_modules/.cache/finco-security/policy.json', 'utf8'))
for (const sriKey of ['loginIntegrity', 'clerkLoginIntegrity', 'clerkAdapterIntegrity']) {
  if (hint[sriKey]) assert(policy.strictCsp.includes(`'${hint[sriKey]}'`),
    `Sign-in module ${sriKey} missing from strict CSP`)
}
assert.match(policy.strictCsp, /strict-dynamic/)
assert(!policy.strictCsp.split('script-src-attr')[0].includes('unsafe-inline'))

const manifest = JSON.parse(await readFile(path.join(dist, '.vite/manifest.json'), 'utf8'))
const entry = Object.keys(manifest).find(key => manifest[key].isEntry)
assert(entry, 'Missing production entry')
const seen = new Set()
function visit(key) {
  if (seen.has(key)) return
  seen.add(key)
  for (const dependency of manifest[key].imports || []) visit(dependency)
}
visit(entry)
let entryGzipBytes = 0
for (const key of seen) {
  assert(!/app-layout|CartesianChart|chat-panel|auth-brand-panel|locales\/pt-BR/.test(key), `Private/decorative dependency in initial entry: ${key}`)
  const file = manifest[key].file
  assert.match(file, /^static\/.+-[\w-]+\.js$/)
  entryGzipBytes += gzipSync(await readFile(path.join(dist, file))).length
}
assert(entryGzipBytes <= 300 * 1024, `Entry graph gzip budget exceeded: ${entryGzipBytes}`)
for (const file of await readdir(path.join(dist, 'static'))) assert(!file.endsWith('.map'), `Public source map: ${file}`)

const catalog = await readFile(path.join(dist, '.well-known/ai-catalog.json'), 'utf8')
assert.equal(await readFile(path.join(dist, 'ai-catalog.json'), 'utf8'), catalog)
const data = JSON.parse(catalog)
assert.equal(data.specVersion, '1.0')
assert.deepEqual(data.entries, [], 'Do not advertise an unverified public agent capability')
assert.match(await readFile(path.join(dist, 'llms.txt'), 'utf8'), /^# FinCo-Pilot/)
assert.match(await readFile(path.join(dist, 'robots.txt'), 'utf8'), /Disallow: \/api\//)
console.log(JSON.stringify({ entryChunks: seen.size, entryGzipBytes, budgetBytes: 300 * 1024, discoveryFiles: 'valid', sourceMaps: 'absent' }, null, 2))

// The same production artifact must contain the real Next.js marketing entry.
const marketing = await readFile(path.join(dist, 'welcome/index.html'), 'utf8')
const publicIndexable = marketingPublicationEnv().NEXT_PUBLIC_MARKETING_INDEXABLE === 'true'
const expectedPublic = ['', 'features/', 'how-it-works/', 'guides/import-transactions/']
const titles = new Set()
const descriptions = new Set()
for (const route of expectedPublic) {
  const page = await readFile(path.join(dist, 'welcome', route, 'index.html'), 'utf8')
  const canonical = `https://fincopilot.app/welcome/${route}`
  assert(page.includes(`<link rel="canonical" href="${canonical}"`), `Incorrect canonical: ${route}`)
  assert.equal((page.match(/<h1\b/g) || []).length, 1)
  const heading = page.match(/<h1\b[^>]*>(.*?)<\/h1>/s)?.[1] || ''
  assert(heading.replace(/<[^>]*>/g, '').trim().length > 5, 'Empty source H1')
  assert(!heading.includes('aria-hidden="true"'), 'Source H1 must be accessible')
  const robots = page.match(/<meta name="robots" content="([^"]+)"/)?.[1]
  assert(robots && robots.includes('noindex') === !publicIndexable, `Indexability mismatch: ${route}`)
  const title = page.match(/<title>(.*?)<\/title>/s)?.[1]
  const description = page.match(/<meta name="description" content="([^"]+)"/)?.[1]
  assert(title && !titles.has(title) && description && !descriptions.has(description), 'Unique metadata required')
  titles.add(title); descriptions.add(description)
}
const rootSitemap = await readFile(path.join(dist, 'sitemap.xml'), 'utf8')
assert.equal(rootSitemap, await readFile(path.join(dist, 'welcome/sitemap.xml'), 'utf8'))
assert.deepEqual([...rootSitemap.matchAll(/<loc>(.*?)<\/loc>/g)].map(m => m[1]),
  publicIndexable ? expectedPublic.map(route => `https://fincopilot.app/welcome/${route}`) : [])
const rootRobots = await readFile(path.join(dist, 'robots.txt'), 'utf8')
assert.equal(rootRobots.includes('Sitemap: https://fincopilot.app/sitemap.xml'), publicIndexable)
for (const route of expectedPublic.slice(1)) assert(marketing.includes(`href="/welcome/${route}"`), `Broken footer href: ${route}`)
assert(marketing.includes('FinCo-Pilot') && marketing.includes('main-content'), 'Landing is missing')
assert(!marketing.includes('finco-app-shell'), 'Finance shell must not replace marketing')
for (const destination of ['/login','/register','/pricing','/privacy','/terms','/support']) assert(marketing.includes(`href="${destination}"`), `Landing CTA missing: ${destination}`)
for (const match of marketing.matchAll(/<script\b[^>]*src="([^"]+)"[^>]*integrity="(sha256-[^"]+)"/g)) {
  assert.match(match[1], /^\/welcome\/_next\/static\//)
  const code = await readFile(path.join(dist, match[1].slice(1)))
  assert.equal(match[2], `sha256-${createHash('sha256').update(code).digest('base64')}`, 'Stale marketing SRI')
  assert(policy.strictCsp.includes(`'${match[2]}'`), 'Marketing SRI absent from strict CSP')
}
const install = JSON.parse(await readFile(path.join(dist,'manifest.webmanifest'),'utf8'))
assert.equal(install.id, '/') // Preserve existing installation identity.
assert.equal(install.start_url, '/dashboard')
console.log('Connected Next.js marketing, same-origin CTAs, marketing SRI/CSP and PWA start URL verified.')
