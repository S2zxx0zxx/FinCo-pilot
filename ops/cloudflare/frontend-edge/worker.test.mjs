import { readdir } from 'node:fs/promises'
import { test } from 'node:test'
import assert from 'node:assert/strict'
import worker, { handleRequest, frontendPath, targetsBackend } from './worker.mjs'

const env = { APP_HOST: 'fincopilot.app', FRONTEND_DEPLOYMENT_ORIGIN: 'https://pinned-example.vercel.app', FRONTEND_DEPLOYMENT_COMMIT: 'synthetic-test-commit' }
test('backend calls keep the exact origin URL, auth, method and body and cannot cache', async () => {
  const request = new Request('https://fincopilot.app/api/private', { method: 'POST', headers: { Authorization: 'Bearer synthetic-test-only' }, body: 'synthetic-body' })
  const response = await handleRequest(request, env, async (forwarded, options) => {
    assert.equal(forwarded, request)
    assert.equal(forwarded.headers.get('authorization'), 'Bearer synthetic-test-only')
    assert.equal(await forwarded.text(), 'synthetic-body')
    assert.equal(options.cf.cacheEverything, false)
    return new Response('denied', { status: 401 })
  })
  assert.equal(response.status, 401)
  assert.equal(response.headers.get('cache-control'), 'no-store')
})
test('frontend shell never forwards credentials, private paths or query tokens', async () => {
  const response = await handleRequest(new Request('https://fincopilot.app/reset-password?token=synthetic-sensitive', { headers: { Authorization: 'Bearer synthetic-secret', Cookie: 'synthetic-private=1', Referer: 'https://fincopilot.app/i/synthetic-token' } }), env, async (request) => {
    assert.equal(request.url, env.FRONTEND_DEPLOYMENT_ORIGIN + '/index.html')
    for (const name of ['authorization', 'cookie', 'referer']) assert.equal(request.headers.get(name), null)
    return new Response('static shell', { headers: { 'X-Robots-Tag': 'noindex', 'Set-Cookie': 'upstream=1' } })
  })
  assert.equal(response.headers.get('cache-control'), 'no-store')
  assert.equal(response.headers.get('set-cookie'), null)
  assert.equal(response.headers.get('x-robots-tag'), null)
})
test('only successful static assets are immutable; errors remain no-store', async () => {
  for (const status of [200, 404, 503]) {
    const response = await handleRequest(new Request('https://fincopilot.app/static/entry-abcdef12.js'), env, async () => new Response('fixture', { status }))
    assert.match(response.headers.get('cache-control'), status === 200 ? /immutable/ : /no-store/)
  }
  assert.equal(frontendPath('/@vite/client'), null)
  assert.equal(frontendPath('/src/main.tsx'), null)
  assert.equal(frontendPath('/assets'), '/index.html')
  assert.equal(targetsBackend('/api/accounts'), true)
  assert.equal(targetsBackend('/mcp'), true)
  assert.equal(targetsBackend('/apiculture'), false)
})
test('invalid pin and origin failure fail closed, without replaying a request', async () => {
  let calls = 0
  const fail = async () => { calls++; throw new Error('synthetic failure') }
  assert.equal((await handleRequest(new Request('https://fincopilot.app/login'), { ...env, FRONTEND_DEPLOYMENT_ORIGIN: 'https://untrusted.example' }, fail)).status, 503)
  assert.equal(calls, 0)
  assert.equal((await handleRequest(new Request('https://fincopilot.app/api/private', { method: 'POST', body: 'fixture' }), env, fail)).status, 502)
  assert.equal(calls, 1)
})

test('runtime entry ignores ExecutionContext and preserves all install/artwork assets', async () => {
  const savedFetch = globalThis.fetch
  globalThis.fetch = async () => new Response('fixture')
  try {
    const response = await worker.fetch(new Request('https://fincopilot.app/login'), env, { waitUntil() {} })
    assert.equal(response.status, 200)
  } finally { globalThis.fetch = savedFetch }
  for (const file of ['/android-icon-192x192.png', '/android-icon-maskable-512x512.png', '/apple-touch-icon.png', '/spaceui/coin.webp', '/spaceui/target.webp']) assert.equal(frontendPath(file), file)
})

test('every real committed public asset has a frontend route, including discovery and artwork', async () => {
  const root = new URL('../../../frontend/public/', import.meta.url)
  const files = await readdir(root, { recursive: true, withFileTypes: true })
  for (const file of files.filter(entry => entry.isFile())) {
    const directory = file.parentPath.slice(root.pathname.length)
    const pathname = '/' + (directory ? directory + '/' : '') + file.name
    assert.equal(frontendPath(pathname), pathname, pathname)
  }
})

test('a development HTML fallback is never returned as a working MCP endpoint', async () => {
  const response = await handleRequest(new Request('https://fincopilot.app/mcp'), env, async () => new Response('<script src="/@vite/client"></script>', { headers: { 'Content-Type': 'text/html' } }))
  assert.equal(response.status, 503)
  assert(! (await response.text()).includes('@vite'))
})
