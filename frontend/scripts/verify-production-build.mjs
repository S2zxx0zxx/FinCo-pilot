/** Production entry regression gate. No network, credentials or private data. */
import assert from 'node:assert/strict'
import { readFile, readdir } from 'node:fs/promises'
import { createHash } from 'node:crypto'
import { gzipSync } from 'node:zlib'
import path from 'node:path'

const dist = path.resolve('dist')
const html = await readFile(path.join(dist, 'index.html'), 'utf8')
assert(!html.includes('/@vite/client') && !html.includes('/src/main.tsx'), 'Development server output must never ship')
assert.match(html, /name="description"/, 'Description missing')
const structured = JSON.parse(html.match(/<script type="application\/ld\+json">(.*?)<\/script>/s)?.[1] || '{}')
assert.equal(structured['@type'], 'WebApplication')
assert.equal(structured.name, 'FinCo-Pilot')

// Independently check delivered entry bytes, not a temporary bundler chunk.
for (const match of html.matchAll(/<(?:script|link)[^>]+(?:src|href)="([^"]+)"[^>]+integrity="(sha256-[^"]+)"/g)) {
  const code = await readFile(path.join(dist, match[1].slice(1)))
  assert.equal(match[2], `sha256-${createHash('sha256').update(code).digest('base64')}`, 'Stale entry SRI')
}
assert.match(html, /integrity="sha256-/)
const policy = JSON.parse(await readFile('node_modules/.cache/finco-security/policy.json', 'utf8'))
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
