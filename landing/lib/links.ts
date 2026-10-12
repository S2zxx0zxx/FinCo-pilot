const fallback = 'https://fincopilot.app'

function getAppOrigin(): string {
  const raw = process.env.NEXT_PUBLIC_FINCO_APP_URL?.trim() || fallback
  try {
    const url = new URL(raw)
    const isLocal = url.hostname === 'localhost' || url.hostname === '127.0.0.1'
    if (url.username || url.password || url.search || url.hash || url.pathname !== '/' ||
        (url.protocol !== 'https:' && !(isLocal && url.protocol === 'http:'))) return fallback
    return url.origin
  } catch { return fallback }
}

/** The original Vite finance app remains the only destination for authenticated routes. */
export const APP_URL = getAppOrigin()
export const APP_LINKS = {
  login: new URL('/login', APP_URL).toString(),
  register: new URL('/register', APP_URL).toString(),
  pricing: new URL('/pricing', APP_URL).toString(),
  support: new URL('/support', APP_URL).toString(),
  privacy: new URL('/privacy', APP_URL).toString(),
  terms: new URL('/terms', APP_URL).toString(),
} as const
