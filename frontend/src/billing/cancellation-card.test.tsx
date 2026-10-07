import { afterEach, expect, it, vi } from 'vitest'
import { screen, waitFor } from '@testing-library/react'
import { renderWithProviders } from '@/test/utils'
import { CancellationCard } from './cancellation-card'
const mocks = vi.hoisted(() => ({ refresh: vi.fn() }))
vi.mock('@/contexts/auth-context', () => ({ useAuth: () => ({ user: { id: 'cancellation-user' }, token: 'synthetic-token' }) }))
vi.mock('@/contexts/billing-context', () => ({ useBilling: () => ({ refreshEntitlements: mocks.refresh }) }))
afterEach(() => { vi.unstubAllGlobals(); vi.clearAllMocks() })
const status = { available: true, state: 'available', paid_through: '2027-01-01T00:00:00Z' }
it('requires explicit consent and sends no browser-selected provider identity', async () => {
  const fetcher = vi.fn().mockImplementation((_url, init?: RequestInit) => Promise.resolve(new Response(JSON.stringify(init?.method === 'POST' ? { ...status, state: 'confirmed' } : status))))
  vi.stubGlobal('fetch', fetcher)
  const { user } = renderWithProviders(<CancellationCard />)
  const button = await screen.findByRole('button', { name: 'Cancel renewals' })
  expect(button).toBeDisabled()
  expect(screen.getByText(/does not issue a refund/)).toBeInTheDocument()
  await user.click(screen.getByRole('checkbox'))
  await user.click(button)
  await screen.findByRole('status')
  expect(screen.getByRole('status')).toHaveTextContent('Renewals are canceled')
  expect(JSON.parse(fetcher.mock.calls[1][1].body)).toEqual({ authorize: true })
  expect(fetcher).toHaveBeenCalledTimes(2)
  await waitFor(() => expect(mocks.refresh).toHaveBeenCalledOnce())
})
it('shows uncertain outcomes as pending and rechecks without requesting new consent', async () => {
  const fetcher = vi.fn().mockResolvedValue(new Response(JSON.stringify({ ...status, state: 'uncertain' })))
  vi.stubGlobal('fetch', fetcher)
  renderWithProviders(<CancellationCard />)
  await screen.findByRole('button', { name: 'Check cancellation' })
  expect(screen.getByRole('status')).toHaveTextContent('awaiting provider confirmation')
  expect(screen.queryByRole('checkbox')).not.toBeInTheDocument()
})
it('does not report cancellation when the provider outcome cannot be verified', async () => {
  const fetcher = vi.fn().mockImplementation((_url, init?: RequestInit) => Promise.resolve(new Response(JSON.stringify(init?.method === 'POST' ? { raw: 'private-provider-error' } : status))))
  vi.stubGlobal('fetch', fetcher)
  const { user } = renderWithProviders(<CancellationCard />)
  await screen.findByRole('button', { name: 'Cancel renewals' })
  await user.click(screen.getByRole('checkbox'))
  await user.click(screen.getByRole('button', { name: 'Cancel renewals' }))
  expect(await screen.findByRole('alert')).toHaveTextContent('could not be verified')
  expect(screen.queryByText('private-provider-error')).not.toBeInTheDocument()
  expect(mocks.refresh).not.toHaveBeenCalled()
})
