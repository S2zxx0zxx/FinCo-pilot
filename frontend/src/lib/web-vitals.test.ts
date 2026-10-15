import { describe, expect, it } from 'vitest'
import type { Metric } from 'web-vitals'
import { summarizeVital } from './web-vitals'

describe('private financial web-vitals reporting', () => {
  it('retains aggregate measurements without leaking URLs, tokens or DOM entries', () => {
    const metric = { name: 'LCP', value: 1234.567, rating: 'good', navigationType: 'navigate', id: 'private-session', entries: [{ name: 'secret-account', element: 'private DOM' }] } as unknown as Metric
    expect(summarizeVital(metric, '/accounts/private-account-id?token=secret')).toEqual({ name: 'LCP', value: 1235, rating: 'good', navigationType: 'navigate', page: 'application' })
    expect(JSON.stringify(summarizeVital(metric, '/reset-password?token=secret'))).not.toMatch(/secret|private-session|entries/)
  })
  it('rejects invalid numbers and unsupported metrics', () => {
    for (const value of [NaN, Infinity, -1]) expect(summarizeVital({ name: 'INP', value } as Metric, '/')).toBeNull()
    expect(summarizeVital({ name: 'FCP', value: 10 } as Metric, '/')).toBeNull()
  })
})
