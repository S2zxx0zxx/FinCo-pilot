export const SUPPORT_LAST_REQUEST_ID_KEY = 'fincopilot:last-request-id'

const REQUEST_REFERENCE_RE = /^FCREQ-[A-F0-9]{12}$/
const SUPPORT_REFERENCE_RE = /^FC-[A-F0-9]{10}$/
const SUPPORT_CATEGORIES = new Set([
  'account_access',
  'billing_payment',
  'bank_connection',
  'transactions_import',
  'safe_to_spend',
  'finco_copilot',
  'bug_performance',
  'privacy_data',
  'feature_request',
  'other',
])

export function normalizeRequestReference(value: unknown): string | null {
  if (typeof value !== 'string') return null
  const normalized = value.trim().toUpperCase()
  return REQUEST_REFERENCE_RE.test(normalized) ? normalized : null
}

export function normalizeSupportReference(value: unknown): string | null {
  if (typeof value !== 'string') return null
  const normalized = value.trim().toUpperCase()
  return SUPPORT_REFERENCE_RE.test(normalized) ? normalized : null
}

export function rememberRequestId(headers: unknown): string | null {
  if (!headers || typeof headers !== 'object') return null
  const values = headers as Record<string, unknown> & { get?: (name: string) => unknown }
  let raw: unknown
  if (typeof values.get === 'function') raw = values.get('x-request-id')
  else raw = values['x-request-id'] ?? values['X-Request-ID']
  const reference = normalizeRequestReference(raw)
  if (!reference) return null
  try {
    window.sessionStorage.setItem(SUPPORT_LAST_REQUEST_ID_KEY, reference)
  } catch {
    // Storage may be disabled; callers still get the current response id.
  }
  return reference
}

export function lastRequestId(): string | null {
  try {
    return normalizeRequestReference(window.sessionStorage.getItem(SUPPORT_LAST_REQUEST_ID_KEY))
  } catch {
    return null
  }
}

export function sanitizeSupportPath(value: string | null | undefined): string | null {
  if (!value) return null
  const trimmed = value.trim()
  if (!trimmed.startsWith('/') || trimmed.startsWith('//') || trimmed.includes('://')) return null
  return trimmed.split('?', 1)[0].split('#', 1)[0].slice(0, 500)
}

export function buildSupportUrl({
  from,
  category,
  reference,
}: {
  from?: string | null
  category?: string | null
  reference?: string | null
} = {}): string {
  const params = new URLSearchParams()
  const safeFrom = sanitizeSupportPath(from)
  const safeReference = normalizeRequestReference(reference)
  if (safeFrom && safeFrom !== '/support') params.set('from', safeFrom)
  if (category && SUPPORT_CATEGORIES.has(category)) params.set('category', category)
  if (safeReference) params.set('ref', safeReference)
  const query = params.toString()
  return query ? `/support?${query}` : '/support'
}
