/**
 * Frontend-only visual preview. Never grants a session or backend privileges.
 * Production builds cannot enable this path, even on localhost.
 */
export const localUiPreview = import.meta.env.DEV &&
  typeof window !== 'undefined' &&
  ['localhost', '127.0.0.1', '::1', '[::1]'].includes(window.location.hostname)
