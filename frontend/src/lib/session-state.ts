export const SESSION_INVALIDATED_EVENT = 'fincopilot:session-invalidated'

/** A late failure for an old request must never clear a replacement session. */
export function invalidateRejectedSession(authorization: unknown): boolean {
  const current = localStorage.getItem('token')
  if (!current || authorization !== `Bearer ${current}`) return false
  localStorage.removeItem('token')
  window.dispatchEvent(new Event(SESSION_INVALIDATED_EVENT))
  return true
}
