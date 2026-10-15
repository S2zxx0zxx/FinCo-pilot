/** Production static frontend over the unchanged same-origin Tunnel backend.
 * No storage bindings, credentials, financial data persistence or request logs.
 * A pinned deployment is required; never use a moving preview branch alias.
 */
const PUBLIC_FILES = new Set([
  "/.well-known/ai-catalog.json",
  "/ai-catalog.json",
  "/android-icon-192x192.png",
  "/android-icon-512x512.png",
  "/android-icon-maskable-512x512.png",
  "/apple-touch-icon.png",
  "/favicon-16x16.png",
  "/favicon-32x32.png",
  "/favicon-96x96.png",
  "/favicon.ico",
  "/finco-favicon.svg",
  "/finco-pwa-icon.svg",
  "/finco-pwa-maskable.svg",
  "/fonts/open-runde/OFL.txt",
  "/fonts/open-runde/open-runde-bold.woff2",
  "/fonts/open-runde/open-runde-medium.woff2",
  "/fonts/open-runde/open-runde-regular.woff2",
  "/fonts/open-runde/open-runde-semibold.woff2",
  "/llms.txt",
  "/manifest.webmanifest",
  "/robots.txt",
  "/spaceui/FLUENT-EMOJI-LICENSE.txt",
  "/spaceui/coin.webp",
  "/spaceui/target.webp",
  "/sw.js"
])

export function targetsBackend(pathname) {
  return pathname === '/api' || pathname.startsWith('/api/') || pathname === '/mcp'
}

export function frontendPath(pathname) {
  if (pathname === '/welcome/' || pathname === '/welcome') return '/welcome/index.html'
  if (pathname.startsWith('/welcome/')) {
    // Only static export paths; no private route, query, credential or SPA fallback.
    return !pathname.includes('..') && /^\/welcome\/[\w./%-]+\.(?:html|txt|js|css|webp|png|svg|ico|woff2|json)$/.test(pathname) ? pathname : null
  }
  if (pathname.startsWith('/static/')) return /^\/static\/[\w.-]+$/.test(pathname) ? pathname : null
  if (PUBLIC_FILES.has(pathname)) return pathname
  if (/^\/(src|node_modules|@vite|\.vite)(\/|$)/.test(pathname)) return null
  // Browser URL stays unchanged. Vercel receives no recovery query, shared
  // invoice token, private account route, cookie or Authorization header.
  return '/index.html'
}

function unavailable(status = 503) {
  return new Response('FinCo-Pilot is temporarily unavailable.', { status, headers: { 'Cache-Control': 'no-store', 'Content-Type': 'text/plain; charset=utf-8', 'X-Content-Type-Options': 'nosniff' } })
}

export async function handleRequest(request, env, fetchImpl = fetch) {
  const url = new URL(request.url)
  if (url.hostname !== env.APP_HOST) return unavailable(404)
  if (targetsBackend(url.pathname)) {
    try {
      // A Worker ROUTE's same-host fetch resolves the existing DNS/Tunnel
      // origin. No database/backend target is changed; method/body/auth stay.
      const response = await fetchImpl(request, { cf: { cacheEverything: false, cacheTtl: 0 } })
      if (response.status === 101) return response
      // The old development frontend may answer /mcp with its HTML shell.
      // Never advertise that shell as a working machine/financial endpoint.
      if (url.pathname === '/mcp' && /text\/html/i.test(response.headers.get('content-type') || '')) return unavailable(503)
      const headers = new Headers(response.headers)
      headers.set('Cache-Control', 'no-store')
      return new Response(response.body, { status: response.status, statusText: response.statusText, headers })
    } catch { return unavailable(502) }
  }
  if (!['GET', 'HEAD'].includes(request.method)) return unavailable(405)
  if (url.pathname === '/') return new Response(null, { status: 302, headers: { Location: '/welcome/', 'Cache-Control': 'no-store', 'Referrer-Policy': 'no-referrer', 'X-Content-Type-Options': 'nosniff', 'X-Frame-Options': 'DENY' } })
  let origin
  try {
    origin = new URL(env.FRONTEND_DEPLOYMENT_ORIGIN)
    if (origin.protocol !== 'https:' || !origin.hostname.endsWith('.vercel.app') || origin.origin !== env.FRONTEND_DEPLOYMENT_ORIGIN) return unavailable()
  } catch { return unavailable() }
  const pathname = frontendPath(url.pathname)
  if (!pathname) return unavailable(404)
  const staticAsset = pathname.startsWith('/static/') || pathname.startsWith('/welcome/_next/static/')
  const headers = new Headers()
  for (const name of ['accept', 'accept-encoding', 'if-none-match', 'if-modified-since', 'range']) {
    const value = request.headers.get(name)
    if (value) headers.set(name, value)
  }
  try {
    const response = await fetchImpl(new Request(origin.origin + pathname, { method: request.method, headers, redirect: 'manual' }), {
      cf: staticAsset ? { cacheEverything: true, cacheTtlByStatus: { '200-299': 31536000, '300-999': -1 } } : { cacheEverything: false, cacheTtl: 0 },
    })
    if (response.status >= 300 && response.status < 400 && response.status !== 304) return unavailable(502)
    const output = new Headers(response.headers)
    output.delete('Set-Cookie')
    output.delete('X-Robots-Tag') // Public production domain; upstream preview is noindex.
    output.set('Referrer-Policy', 'no-referrer')
    output.set('X-Content-Type-Options', 'nosniff')
    output.set('X-FinCo-Frontend-Commit', env.FRONTEND_DEPLOYMENT_COMMIT)
    output.set('Cache-Control', staticAsset && response.ok ? 'public, max-age=31536000, immutable' : 'no-store')
    return new Response(response.body, { status: response.status, statusText: response.statusText, headers: output })
  } catch { return unavailable(502) }
}

export default { fetch(request, env) { return handleRequest(request, env) } }
