import { afterEach, beforeEach, expect, it, vi } from 'vitest'
import { screen, waitFor } from '@testing-library/react'
import { renderWithProviders } from '@/test/utils'
import { RenewalEnrollmentCard } from './renewal-enrollment-card'
import type { RazorpayConstructor, RazorpaySubscriptionCheckoutOptions } from '@/types/razorpay'
const mocks = vi.hoisted(() => ({ refresh: vi.fn(), error: vi.fn(), success: vi.fn(), entitlements: null as null | { status: string, grace_until?: string } }))
vi.mock('@/contexts/auth-context', () => ({ useAuth: () => ({ user: { id: 'renewal-user' }, token: 'synthetic-token' }) }))
vi.mock('@/contexts/billing-context', () => ({ useBilling: () => ({ plan: 'pro', entitlements: mocks.entitlements, refreshEntitlements: mocks.refresh }) }))
vi.mock('@/lib/razorpay-sdk', () => ({ ensureRazorpaySdk: () => Promise.resolve() }))
vi.mock('sonner', () => ({ toast: { error: mocks.error, success: mocks.success } }))
const quote = { available: true, plan: 'pro', interval: 'monthly', amount_minor: 9900, currency: 'INR' }
const bound = { ...quote, key_id: 'rzp_test_Synthetic', subscription_id: 'sub_Synthetic', total_count: 3, starts_at: '2027-01-01T00:00:00Z' }
let options: RazorpaySubscriptionCheckoutOptions
let opens = 0
beforeEach(() => {
  vi.clearAllMocks(); opens = 0; mocks.entitlements = null
  window.Razorpay = class { constructor(value: RazorpaySubscriptionCheckoutOptions) { options = value } open() { opens++ } on() {} } as unknown as RazorpayConstructor
})
afterEach(() => { vi.unstubAllGlobals(); delete window.Razorpay })
async function start(response = bound) {
  const fetcher = vi.fn().mockImplementation((_url, init?: RequestInit) => Promise.resolve(new Response(JSON.stringify(init?.method === 'POST' ? response : quote), { status: 200 })))
  vi.stubGlobal('fetch', fetcher)
  const view = renderWithProviders(<RenewalEnrollmentCard />)
  await screen.findByRole('button', { name: 'Authorize renewals' })
  return { ...view, fetcher }
}
it('requires an explicitly selected count and consent before creating a mandate', async () => {
  const { user, fetcher } = await start()
  const button = screen.getByRole('button', { name: 'Authorize renewals' })
  expect(button).toBeDisabled()
  await user.type(screen.getByRole('spinbutton'), '3')
  expect(button).toBeDisabled()
  await user.click(screen.getByRole('checkbox'))
  await user.click(button)
  await waitFor(() => expect(opens).toBe(1))
  expect(JSON.parse(fetcher.mock.calls[1][1].body)).toEqual({ total_count: 3, authorize: true })
  expect(options.subscription_id).toBe('sub_Synthetic')
  expect(options).not.toHaveProperty('order_id')
  await user.click(button)
  expect(opens).toBe(1)
  expect(fetcher).toHaveBeenCalledTimes(2)
})
it('rejects a live key without opening checkout', async () => {
  const { user } = await start({ ...bound, key_id: 'rzp_live_Synthetic' })
  await user.type(screen.getByRole('spinbutton'), '3')
  await user.click(screen.getByRole('checkbox'))
  await user.click(screen.getByRole('button', { name: 'Authorize renewals' }))
  await waitFor(() => expect(mocks.error).toHaveBeenCalled())
  expect(opens).toBe(0)
  expect(mocks.refresh).not.toHaveBeenCalled()
})
it('does not treat a foreign authorization callback as paid service', async () => {
  const { user } = await start()
  await user.type(screen.getByRole('spinbutton'), '3')
  await user.click(screen.getByRole('checkbox'))
  await user.click(screen.getByRole('button', { name: 'Authorize renewals' }))
  await waitFor(() => expect(opens).toBe(1))
  await options.handler({ razorpay_subscription_id: 'sub_Foreign', razorpay_payment_id: 'pay_Synthetic', razorpay_signature: 'a'.repeat(64) })
  expect(mocks.error).toHaveBeenCalled()
  expect(mocks.success).not.toHaveBeenCalled()
  expect(mocks.refresh).not.toHaveBeenCalled()
})

it.each(['grace', 'past_due'])('shows %s recovery without requesting another mandate', async (status) => {
  mocks.entitlements = { status, grace_until: '2027-01-02T00:00:00Z' }
  const fetcher = vi.fn()
  vi.stubGlobal('fetch', fetcher)
  renderWithProviders(<RenewalEnrollmentCard />)
  expect(screen.getByRole('status')).toHaveTextContent('Renewal payment needs attention')
  expect(screen.queryByRole('button', { name: 'Authorize renewals' })).not.toBeInTheDocument()
  expect(fetcher).not.toHaveBeenCalled()
  expect(opens).toBe(0)
})
