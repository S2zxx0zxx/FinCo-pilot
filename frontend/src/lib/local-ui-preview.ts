/**
 * Temporary public, frontend-only UI preview while real sign-in is paused.
 * Set VITE_LOGIN_PAUSED=false on the frontend build and redeploy to restore
 * normal login, registration and dashboard routes without further code changes.
 * This does NOT bypass any backend authentication or expose financial data.
 */
export const loginPaused = import.meta.env.PROD && import.meta.env.VITE_LOGIN_PAUSED !== 'false'

/** Standalone visual preview may also be reached on Vite's loopback dev server. */
export const localUiPreview = import.meta.env.DEV &&
  typeof window !== 'undefined' &&
  ['localhost', '127.0.0.1', '::1', '[::1]'].includes(window.location.hostname)

export const uiPreviewAvailable = loginPaused || localUiPreview
