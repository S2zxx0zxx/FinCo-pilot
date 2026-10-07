import { afterEach, expect, it, vi } from 'vitest'
import { screen, waitFor } from '@testing-library/react'
import { renderWithProviders } from '@/test/utils'
import { CheckoutStatusCard } from './checkout-status-card'
const mocks = vi.hoisted(() => ({ entitlements: vi.fn(), campaign: vi.fn() }))
vi.mock('@/contexts/auth-context', () => ({ useAuth: () => ({ user: { id: 'synthetic-owner' }, token: 'synthetic-token' }) }))
vi.mock('@/contexts/billing-context', () => ({ useBilling: () => ({ refreshEntitlements: mocks.entitlements, refreshFounderCampaign: mocks.campaign }) }))
afterEach(() => { vi.unstubAllGlobals(); vi.clearAllMocks() })
it('rechecks failed payment with GET without a new SDK or financial POST', async () => {
  const fetcher = vi.fn().mockImplementation(() => Promise.resolve(new Response(JSON.stringify({ available: true, checkout: { state: 'failed', test_mode: true, activation_confirmed: false } }))))
  vi.stubGlobal('fetch', fetcher)
  const { user } = renderWithProviders(<CheckoutStatusCard />)
  expect(await screen.findByText(/may still resolve later/)).toBeInTheDocument()
  expect(screen.getByText(/Test Mode/)).toBeInTheDocument()
  await user.click(screen.getByRole('button', { name: 'Check payment status' }))
  await waitFor(() => expect(fetcher).toHaveBeenCalledTimes(2))
  expect(fetcher.mock.calls.every(([url, options]) => url === '/api/checkout/status' && options.method === undefined)).toBe(true)
  await waitFor(() => expect(mocks.entitlements).toHaveBeenCalled())
})
it('does not render untrusted raw status and safely offers support', async () => {
  vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response(JSON.stringify({ available: true, checkout: { state: 'private-bank-canary', test_mode: true, activation_confirmed: false } }))))
  renderWithProviders(<CheckoutStatusCard />)
  expect(await screen.findByText(/could not be confirmed/)).toBeInTheDocument()
  expect(screen.queryByText(/private-bank-canary/)).not.toBeInTheDocument()
  expect(screen.getByRole('link', { name: 'Contact support' })).toHaveAttribute('href', '/support?from=%2Fpricing&category=billing_payment')
})
