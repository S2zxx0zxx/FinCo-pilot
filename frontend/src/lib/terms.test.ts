import { afterEach, expect, it, vi } from 'vitest'
import { fetchTerms } from './terms'

const termsFixture = {
  version: 'v1', reviewed_on: '2026-10-04', status: 'draft' as const, effective_date: null,
  operator: { brand_name: 'FinCo-Pilot', legal_name: null, entity_type: 'individual', country_code: 'IN' },
  contact: { name: null, email: null, address: null, phone: null, designation: null, website: null },
  commercial: { refund_policy: { en: null, hi: null }, cancellation_policy: { en: null, hi: null },
    live_payments: false as const, automatic_paid_activation: false as const, recurring_billing: false as const, automated_refunds: false as const,
    tax_display_mode: 'inclusive', prices: [{ plan: 'free', interval: 'none', amount_minor: 0, currency: 'INR' as const }] },
  sections: [{ id: 'scope', title: { en: 'Scope', hi: 'दायरा' }, body: { en: 'Real service scope', hi: 'वास्तविक सेवा का दायरा' } }],
}
afterEach(() => { vi.unstubAllGlobals(); localStorage.removeItem('token') })
it('fetches public terms without tokens, cookies or workspace headers', async () => {
  localStorage.setItem('token', 'private-canary')
  const fetchMock = vi.fn().mockResolvedValue({ ok: true, json: async () => termsFixture })
  vi.stubGlobal('fetch', fetchMock)
  expect(await fetchTerms()).toEqual(termsFixture)
  expect(fetchMock).toHaveBeenCalledWith('/api/terms', { cache: 'no-store', credentials: 'omit', headers: { Accept: 'application/json' } })
})
it('fails closed for unsuccessful or malformed responses', async () => {
  vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: false }))
  await expect(fetchTerms()).rejects.toThrow('Terms unavailable')
  vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: true, json: async () => ({ status: 'published' }) }))
  await expect(fetchTerms()).rejects.toThrow()
})
it('does not accept a response inventing operational paid capabilities', async () => {
  vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: true, json: async () => ({ ...termsFixture, commercial: { ...termsFixture.commercial, live_payments: true } }) }))
  await expect(fetchTerms()).rejects.toThrow()
})
