import { afterEach, expect, it, vi } from 'vitest'
import { fetchPrivacyPolicy } from './privacy-policy'
afterEach(() => vi.unstubAllGlobals())
it('does not attach session credentials, tokens or workspace identifiers', async () => {
  localStorage.setItem('token', 'private-token')
  const payload = { version: 'v1', reviewed_on: '2026-10-04', status: 'draft', effective_date: null,
    operator: { brand_name: 'FinCo-Pilot', legal_name: null, entity_type: 'individual', country_code: 'IN' },
    contact: { name: null, email: null, address: null }, deployment: { providers: null, locations: null }, sections: [] }
  const fetchMock = vi.fn().mockResolvedValue({ ok: true, json: async () => payload })
  vi.stubGlobal('fetch', fetchMock)
  await fetchPrivacyPolicy()
  expect(fetchMock).toHaveBeenCalledWith('/api/privacy-policy', { cache: 'no-store', credentials: 'omit', headers: { Accept: 'application/json' } })
  localStorage.removeItem('token')
})
it('rejects malformed success responses so the page can show its retry state', async () => {
  vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: true, json: async () => ({ status: 'published' }) }))
  await expect(fetchPrivacyPolicy()).rejects.toThrow()
})
it('rejects a server failure without exposing its response body', async () => {
  vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: false }))
  await expect(fetchPrivacyPolicy()).rejects.toThrow('Privacy notice unavailable')
})
