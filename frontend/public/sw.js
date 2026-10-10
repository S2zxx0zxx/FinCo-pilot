/* FinCo-Pilot service worker
 *
 * Deliberately conservative for a finance application:
 * - app shell and immutable build assets may be cached;
 * - /api requests are never placed in Cache Storage;
 * - user-uploaded/same-origin images are not generically cached;
 * - write requests are never replayed in the background;
 * - updates wait for explicit user approval before taking control.
 */

const VERSION = 'finco-pwa-v5'
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
  '/android-icon-512x512.png',
  '/android-icon-maskable-512x512.png',
]

const PUBLIC_ASSETS = new Set(APP_SHELL.filter((url) => url !== '/'))

function publicResponse(response) {
  return response.ok && !response.redirected && response.type !== 'opaque'
}

async function isAppShell(response) {
  if (!publicResponse(response) || !response.headers.get('content-type')?.includes('text/html')) return false
  const url = new URL(response.url)
  if (url.origin !== self.location.origin || url.pathname !== '/' || url.search) return false
  return /<meta\s+name=["']finco-app-shell["']\s+content=["']v1["']\s*\/?\s*>/.test(await response.clone().text())
}

async function trimCache(cache, maxEntries) {
  const keys = await cache.keys()
  if (keys.length <= maxEntries) return
  await Promise.all(keys.slice(0, keys.length - maxEntries).map((key) => cache.delete(key)))
}

/**
 * Vite's entry filenames are content-hashed and therefore unknown when this
 * source file is authored. Parse the built index document at runtime and warm
 * only its /static/ JS/CSS entry assets. That makes the installed shell usable
 * after the first install without introducing a broad cache of user data.
 */
async function warmStaticAssetsFromDocument(response) {
  try {
    const html = await response.clone().text()
    const urls = new Set()
    const assetPattern = /(?:src|href)=["'](\/static\/[^"'?#]+(?:\?[^"']*)?)["']/g
    let match
    while ((match = assetPattern.exec(html)) !== null) urls.add(match[1])
    if (urls.size === 0) return

    const cache = await caches.open(STATIC_CACHE)
    await Promise.allSettled(
      [...urls].map(async (url) => {
        const cached = await cache.match(url)
        if (cached) return
        const asset = await fetch(url, { cache: 'reload' })
        if (publicResponse(asset)) await cache.put(url, asset)
      }),
    )
    await trimCache(cache, MAX_STATIC_ENTRIES)
  } catch {
    // Shell warming is an optimisation; a failure must never abort install.
  }
}

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(SHELL_CACHE).then(async (cache) => {
      const shellResponse = await fetch('/', { cache: 'no-store' })
      // Access login HTML, redirects and recovery documents are never shells.
      // Reject the install rather than replace a working offline release.
      if (!(await isAppShell(shellResponse))) throw new Error('Public application shell unavailable')
      await cache.put('/', shellResponse.clone())
      await warmStaticAssetsFromDocument(shellResponse)
      // addAll is intentionally avoided so one optional icon cannot prevent the
      // whole worker from installing on an older deployment.
      await Promise.allSettled(
        [...PUBLIC_ASSETS].map(async (url) => {
          const response = await fetch(url, { cache: 'no-cache' })
          if (publicResponse(response)) await cache.put(url, response)
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
    event.waitUntil(self.skipWaiting())
  }
})

async function networkFirstNavigation(request) {
  const cache = await caches.open(SHELL_CACHE)
  try {
    // Only installation writes the canonical shell. Route documents, recovery
    // URLs and proxy sign-in pages must never replace the offline document.
    return await fetch(request)
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
  if (publicResponse(response) && !/no-store|private/i.test(response.headers.get('cache-control') || '')) {
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
  if (publicResponse(response)) await cache.put(request, response.clone())
  return response
}

self.addEventListener('fetch', (event) => {
  const request = event.request
  if (request.method !== 'GET') return

  const url = new URL(request.url)
  if (url.origin !== self.location.origin) return

  // Financial/user data is intentionally left entirely to the network and the
  // application's authenticated data layer. Never put /api responses in the
  // browser Cache Storage.
  if (url.pathname === '/api' || url.pathname.startsWith('/api/') || url.pathname === '/mcp' || url.pathname.startsWith('/mcp/')) return
  if (url.search || request.headers.has('authorization') || ['/reset-password', '/verify-email', '/oauth/callback'].includes(url.pathname)) return

  if (request.mode === 'navigate') {
    event.respondWith(networkFirstNavigation(request))
    return
  }


  if (url.pathname.startsWith('/static/')) {
    event.respondWith(cacheFirstStatic(request))
    return
  }

  if (PUBLIC_ASSETS.has(url.pathname)) {
    event.respondWith(cacheFirstPublicAsset(request))
  }
})
