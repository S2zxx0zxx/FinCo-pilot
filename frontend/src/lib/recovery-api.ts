async function postJson(path: string, body: Record<string, unknown>) {
  const response = await fetch(`/api/auth${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  if (!response.ok) {
    let detail = 'Request failed'
    try {
      const payload = await response.json()
      detail = typeof payload?.detail === 'string' ? payload.detail : detail
    } catch {
      // Preserve generic error: auth recovery endpoints should not leak detail.
    }
    throw new Error(detail)
  }
  if (response.status === 204) return null
  const text = await response.text()
  return text ? JSON.parse(text) : null
}

export const recoveryApi = {
  forgotPassword: (email: string) => postJson('/forgot-password', { email }),
  resetPassword: (token: string, password: string) =>
    postJson('/reset-password', { token, password }),
  requestVerification: (email: string) => postJson('/request-verify-token', { email }),
  verifyEmail: (token: string) => postJson('/verify', { token }),
}
