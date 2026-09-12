/* FinCo-Pilot service worker
 *
 * Deliberately conservative for a finance application:
 * - app shell and immutable build assets may be cached;
 * - /api requests are never placed in Cache Storage;
 * - user-uploaded/same-origin images are not generically cached;
 * - write requests are never replayed in the background;
 * - updates wait for explicit user approval before taking control.
 */

const VERSION = 'finco-pwa-v1'
const SHELL_CACHE = `${VERSION}:shell`
const STATIC_CACHE = `${VERSION}:static`
const CACHE_PREFIX = 'finco-pwa-'
const MAX_STATIC_ENTRIES = 96

const APP_SHELL = [
  '/',
  '/manifest.webmanifest',
  '/finco-favicon.svg',
  '/finco-pwa-icon.svg',
  '/finco-pwa-maskable.svg',
  '/favicon-16x16.png',
  '/favicon-32x32.png',
  '/favicon-96x96.png',
  '/apple-touch-icon.png',
  '/android-icon-192x192.png',
]

const PUBLIC_ASSETS = new Set(APP_SHELL.filter((url) => url !== '/'))

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(SHELL_CACHE).then(async (cache) => {
      // addAll is intentionally avoided so one optional icon cannot prevent the
      // whole worker from installing on an older deployment.
      await Promise.allSettled(
        APP_SHELL.map(async (url) => {
          const response = await fetch(url, { cache: 'no-cache' })
          if (response.ok) await cache.put(url, response)
        }),
      )
    }),
  )
})

self.addEventListener('activate', (event) => {
  event.waitUntil(
    (async () => {
      const keys = await caches.keys()
      await Promise.all(
        keys
          .filter((key) => key.startsWith(CACHE_PREFIX) && ![SHELL_CACHE, STATIC_CACHE].includes(key))
          .map((key) => caches.delete(key)),
      )
      await self.clients.claim()
    })(),
  )
})

self.addEventListener('message', (event) => {
  if (event.data?.type === 'SKIP_WAITING') {
    void self.skipWaiting()
  }
})

async function trimCache(cache, maxEntries) {
  const keys = await cache.keys()
  if (keys.length <= maxEntries) return
  await Promise.all(keys.slice(0, keys.length - maxEntries).map((key) => cache.delete(key)))
}

async function networkFirstNavigation(request) {
  const cache = await caches.open(SHELL_CACHE)
  try {
    const response = await fetch(request)
    if (response.ok) {
      // Store the SPA document under / so every client-side route has one safe
      // offline fallback without persisting any route-specific API response.
      await cache.put('/', response.clone())
    }
    return response
  } catch {
    const cached = await cache.match('/')
    if (cached) return cached

    return new Response(
      '<!doctype html><html><head><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="theme-color" content="#000000"><title>FinCo-Pilot</title></head><body style="margin:0;background:#000;color:#fff;font-family:system-ui;display:grid;place-items:center;min-height:100vh"><main style="text-align:center;padding:32px"><h1 style="margin:0 0 8px">FinCo-Pilot</h1><p style="opacity:.65;margin:0">You are offline. Reconnect to continue.</p></main></body></html>',
      { status: 503, headers: { 'Content-Type': 'text/html; charset=utf-8' } },
    )
  }
}

async function cacheFirstStatic(request) {
  const cache = await caches.open(STATIC_CACHE)
  const cached = await cache.match(request)
  if (cached) return cached

  const response = await fetch(request)
  if (response.ok) {
    await cache.put(request, response.clone())
    await trimCache(cache, MAX_STATIC_ENTRIES)
  }
  return response
}

async function cacheFirstPublicAsset(request) {
  const cache = await caches.open(SHELL_CACHE)
  const cached = await cache.match(request)
  if (cached) return cached

  const response = await fetch(request)
  if (response.ok) await cache.put(request, response.clone())
  return response
}

self.addEventListener('fetch', (event) => {
  const request = event.request
  if (request.method !== 'GET') return

  const url = new URL(request.url)

  // Financial/user data is intentionally left entirely to the network and the
  // application's authenticated data layer. Never put /api responses in the
  // browser Cache Storage.
  if (url.origin === self.location.origin && url.pathname.startsWith('/api/')) return

  if (request.mode === 'navigate') {
    event.respondWith(networkFirstNavigation(request))
    return
  }

  if (url.origin !== self.location.origin) return

  if (url.pathname.startsWith('/static/')) {
    event.respondWith(cacheFirstStatic(request))
    return
  }

  if (PUBLIC_ASSETS.has(url.pathname)) {
    event.respondWith(cacheFirstPublicAsset(request))
  }
})
