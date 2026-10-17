/** Optional, privacy-first frontend error reporting.
 * Never transmit bank data, URL tokens, auth state, breadcrumbs or session replay.
 * Production only reports when explicitly enabled AND configured.
 */

declare const __APP_VERSION__: string

let initialized = false
let sentryModule: { captureException: (error: Error) => void } | null = null

export function sanitizeSentryEvent<T extends object>(event: T): T {
  const raw = event as Record<string, unknown>
  for (const key of [
    'request', 'user', 'contexts', 'breadcrumbs', 'extra', 'tags',
    'message', 'logentry', 'transaction', 'fingerprint', 'modules',
  ]) {
    delete raw[key]
  }
  const exception = raw.exception
  if (exception && typeof exception === 'object') {
    const values = (exception as Record<string, unknown>).values
    if (Array.isArray(values)) {
      for (const value of values) {
        if (!value || typeof value !== 'object') continue
        const error = value as Record<string, unknown>
        if ('value' in error) error.value = '[redacted]'
        const trace = error.stacktrace
        if (!trace || typeof trace !== 'object') continue
        const frames = (trace as Record<string, unknown>).frames
        if (!Array.isArray(frames)) continue
        for (const item of frames) {
          if (!item || typeof item !== 'object') continue
          const frame = item as Record<string, unknown>
          for (const key of ['vars', 'pre_context', 'post_context', 'context_line', 'abs_path']) {
            delete frame[key]
          }
          if (typeof frame.filename === 'string') {
            frame.filename = frame.filename.split('?')[0].split('#')[0]
          }
        }
      }
    }
  }
  raw.tags = { component: 'web' }
  return event
}

export function initSentry(): boolean {
  if (initialized) return true
  if (import.meta.env.VITE_SENTRY_ENABLED !== 'true') return false
  const dsn = String(import.meta.env.VITE_SENTRY_DSN || '').trim()
  if (!dsn) return false
  try {
    const parsed = new URL(dsn)
    if (parsed.protocol !== 'https:' || !parsed.username || parsed.password) return false
  } catch {
    return false
  }

  const rawEnvironment = String(import.meta.env.VITE_SENTRY_ENVIRONMENT || import.meta.env.MODE)
  const environment = ['production', 'staging', 'preview', 'development', 'test'].includes(rawEnvironment)
    ? rawEnvironment : 'unknown'

  // Statically analyzable dynamic import: a bare @vite-ignore package name
  // cannot resolve in a production browser without an import map.
  import('@sentry/react')
    .then((Sentry) => {
      Sentry.init({
        dsn,
        environment,
        release: typeof __APP_VERSION__ !== 'undefined' ? __APP_VERSION__ : 'unknown',
        tracesSampleRate: 0,
        replaysSessionSampleRate: 0,
        replaysOnErrorSampleRate: 0,
        beforeBreadcrumb: () => null,
        beforeSend: (event) => sanitizeSentryEvent(event),
      })
      sentryModule = Sentry
      initialized = true
    })
    .catch(() => {
      // Sentry package not installed or failed to load
    })

  return true
}

export function captureAppError(error: Error): void {
  if (initialized && sentryModule) {
    sentryModule.captureException(error)
  }
}
