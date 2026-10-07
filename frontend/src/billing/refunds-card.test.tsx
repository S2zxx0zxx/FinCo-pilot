import { afterEach, expect, it, vi } from 'vitest'
import { screen } from '@testing-library/react'
import { renderWithProviders } from '@/test/utils'
import { RefundsCard } from './refunds-card'
vi.mock('@/contexts/auth-context', () => ({ useAuth: () => ({ user: { id: 'refund-user' }, token: 'synthetic-token' }) }))
afterEach(() => { vi.unstubAllGlobals(); vi.clearAllMocks() })
it('distinguishes processing and processed without promising bank credit', async () => {
  const fetcher = vi.fn().mockImplementation(() => Promise.resolve(new Response(JSON.stringify({ available: true,
    refunds: [{ id: 'one', state: 'pending', amount_minor: 9900, currency: 'INR' }],
    provider_refunds: [{ id: 'two', state: 'processed', amount_minor: 1000, currency: 'INR' }] }))))
  vi.stubGlobal('fetch', fetcher)
  renderWithProviders(<RefundsCard />)
  await screen.findByText(/Bank credit is not yet confirmed/)
  expect(screen.getByText(/Bank credit timing can vary/)).toBeInTheDocument()
  expect(screen.getByRole('link', { name: 'Request review' })).toHaveAttribute('href', '/support')
  expect(fetcher.mock.calls[0][1].method).toBeUndefined()
})
it('does not expose raw errors or invent a successful refund', async () => {
  vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response(JSON.stringify({ private: 'private-provider-error' }))))
  renderWithProviders(<RefundsCard />)
  expect(await screen.findByRole('alert')).toHaveTextContent('unavailable')
  expect(screen.queryByText('private-provider-error')).not.toBeInTheDocument()
})
it('hides the default-disabled feature', async () => {
  vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response(JSON.stringify({ available: false }))))
  renderWithProviders(<RefundsCard />)
  expect(screen.queryByRole('heading', { name: 'Refunds' })).not.toBeInTheDocument()
})
