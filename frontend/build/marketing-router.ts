import { readFile, stat } from 'node:fs/promises'
import path from 'node:path'
import type { Connect, Plugin } from 'vite'

/** Preview/dev parity with production nginx: marketing never falls into SPA HTML. */
function marketingMiddleware(directory: string): Connect.NextHandleFunction {
  return async (request, response, next) => {
    const pathname = new URL(request.url || '/', 'http://localhost').pathname
    if ((pathname === '/' || pathname === '/welcome' || pathname.startsWith('/welcome/')) && request.method !== 'GET' && request.method !== 'HEAD') { response.writeHead(405).end(); return }
    if (pathname === '/') {
      response.writeHead(302, { Location: '/welcome/', 'Cache-Control': 'no-store' }).end()
      return
    }
    if (pathname === '/welcome') {
      response.writeHead(302, { Location: '/welcome/', 'Cache-Control': 'no-store' }).end()
      return
    }
    if (!pathname.startsWith('/welcome/')) { next(); return }
    if (request.method !== 'GET' && request.method !== 'HEAD') { response.writeHead(405).end(); return }
    const types: Record<string, string> = { '.html':'text/html; charset=utf-8', '.js':'application/javascript', '.css':'text/css', '.json':'application/json', '.txt':'text/plain', '.svg':'image/svg+xml', '.png':'image/png', '.webp':'image/webp', '.woff2':'font/woff2', '.ico':'image/x-icon' }
    try {
      const relative = decodeURIComponent(pathname.slice('/welcome/'.length)) || 'index.html'
      const file = path.resolve(directory, relative)
      if (!file.startsWith(directory + path.sep) || !(await stat(file)).isFile()) throw new Error('Missing marketing file')
      const body = await readFile(file)
      response.writeHead(200, { 'Content-Type': types[path.extname(file)] || 'application/octet-stream', 'Cache-Control':'no-store', 'X-Content-Type-Options':'nosniff' })
      response.end(request.method === 'HEAD' ? undefined : body)
    } catch { response.writeHead(404, { 'Cache-Control':'no-store' }).end('Marketing file unavailable') }
  }
}
export function marketingRouterPlugin(root: string): Plugin {
  return {
    name: 'finco-marketing-entry',
    configureServer(server) { server.middlewares.use(marketingMiddleware(path.join(root, 'public/welcome'))) },
    configurePreviewServer(server) { server.middlewares.use(marketingMiddleware(path.join(root, 'dist/welcome'))) },
  }
}
