import type { Metric } from 'web-vitals'

export const WEB_VITAL_EVENT = 'finco:web-vital'

/** No URLs, selectors, performance entries, session IDs or financial data. */
export function summarizeVital(metric: Metric, route: string) {
  if (!['LCP', 'INP', 'CLS'].includes(metric.name) || !Number.isFinite(metric.value) || metric.value < 0) return null
  return {
    name: metric.name,
    value: metric.name === 'CLS' ? Math.round(metric.value * 1000) / 1000 : Math.round(metric.value),
    rating: metric.rating,
    navigationType: metric.navigationType,
    page: /^\/(login|sign-in|register|sign-up|sso-callback|forgot-password|reset-password|verify-email)(\/|$)/.test(route)
      ? 'authentication' : /^\/(pricing|support|terms|privacy)(\/|$)/.test(route) ? 'public' : 'application',
  }
}

let started = false

/** Explicit opt-in; local events only. A reviewed collector must subscribe.
 * This does not create CrUX data or silently introduce a telemetry endpoint.
 */
export async function initWebVitals() {
  if (started || import.meta.env.VITE_WEB_VITALS_ENABLED !== 'true') return
  started = true
  const route = window.location.pathname
  try {
    const { onCLS, onINP, onLCP } = await import('web-vitals')
    const report = (metric: Metric) => {
      const detail = summarizeVital(metric, route)
      if (detail) window.dispatchEvent(new CustomEvent(WEB_VITAL_EVENT, { detail }))
    }
    onCLS(report)
    onINP(report)
    onLCP(report)
  } catch {
    // Monitoring failure must not prevent access to the application.
    started = false
  }
}
