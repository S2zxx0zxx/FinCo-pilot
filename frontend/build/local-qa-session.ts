import type { Plugin } from 'vite'

/**
 * Development-only, loopback-only helper for a separately provisioned QA database.
 *
 * It exchanges private, server-side QA credentials for a NORMAL application
 * session via the existing /api/auth/login endpoint. It never mints tokens,
 * bypasses MFA, touches production credentials, or modifies backend guards.
 */
export function localQaSessionPlugin(settings: {
  mode: string
  enabled: boolean
  frontendUrl?: string
  backendUrl?: string
  email?: string
  password?: string
}): Plugin {
  return {
    name: 'finco-loopback-qa-session',
    apply: 'serve',
    configureServer(server) {
      const ready = settings.mode === 'development' &&
        settings.enabled &&
        settings.frontendUrl === 'http://localhost:3300' &&
        settings.backendUrl === 'http://backend:8000' &&
        Boolean(settings.email?.includes('@')) &&
        Boolean(settings.password && settings.password.length >= 24)

      // Nothing is registered outside the explicitly isolated QA Compose stack.
      if (!ready) return

      server.middlewares.use((req, res, next) => {
        if (req.url?.split('?')[0] !== '/__qa/session') return next()

        const reply = (status: number, body: string) => {
          res.statusCode = status
          res.setHeader('Content-Type', 'application/json; charset=utf-8')
          res.setHeader('Cache-Control', 'no-store')
          res.setHeader('X-Content-Type-Options', 'nosniff')
          res.end(JSON.stringify({ error: body }))
        }

        // QA runs on localhost:3300 only. No wildcard origins, no GET tokens.
        if (req.method !== 'POST') return reply(405, 'method_not_allowed')
        if (req.headers.host !== 'localhost:3300' ||
          req.headers.origin !== 'http://localhost:3300' ||
          req.headers['sec-fetch-site'] !== 'same-origin' ||
          req.headers['x-finco-qa-session'] !== '1') {
          return reply(403, 'local_qa_only')
        }

        void (async () => {
          try {
            const credentials = new URLSearchParams({
              username: settings.email!,
              password: settings.password!,
            })
            const response = await fetch('http://backend:8000/api/auth/login', {
              method: 'POST',
              headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
              body: credentials,
              redirect: 'error',
              signal: AbortSignal.timeout(8000),
            })
            if (!response.ok) return reply(503, 'qa_account_not_ready')
            const data: unknown = await response.json()
            if (!data || typeof data !== 'object' ||
              !('access_token' in data) ||
              typeof data.access_token !== 'string' ||
              !data.access_token) {
              return reply(503, 'qa_interactive_auth_not_supported')
            }
            res.statusCode = 200
            res.setHeader('Content-Type', 'application/json; charset=utf-8')
            res.setHeader('Cache-Control', 'no-store')
            res.setHeader('X-Content-Type-Options', 'nosniff')
            res.end(JSON.stringify({ access_token: data.access_token }))
          } catch {
            reply(503, 'qa_backend_unavailable')
          }
        })()
      })
    },
  }
}
