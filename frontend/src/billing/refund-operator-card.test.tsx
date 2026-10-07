import { afterEach, expect, it, vi } from 'vitest'
import { screen } from '@testing-library/react'
import { renderWithProviders } from '@/test/utils'
import { RefundOperatorCard } from './refund-operator-card'
vi.mock('@/contexts/auth-context', () => ({ useAuth: () => ({ user: { id: 'operator', is_superuser: true }, token: 'synthetic-token' }) }))
afterEach(() => { vi.unstubAllGlobals(); vi.clearAllMocks() })
const payment = { source_kind: 'activation', source_id: 'local-grant', user_id: 'actual-owner', amount_minor: 9900, currency: 'INR' }
it('requires a reviewed amount, evidence and consent and sends only the local payment source', async () => {
  const fetcher = vi.fn().mockImplementation((_url, init?: RequestInit) => Promise.resolve(new Response(JSON.stringify(init?.method === 'POST' ? { state: 'uncertain' } : { available: true, payments: [payment] }))))
  vi.stubGlobal('fetch', fetcher)
  const { user } = renderWithProviders(<RefundOperatorCard />)
  const button = await screen.findByRole('button', { name: 'Authorize or reconcile refund' })
  expect(button).toBeDisabled()
  await user.selectOptions(screen.getByRole('combobox'), 'activation:local-grant')
  await user.type(screen.getByLabelText('Approved amount in paise'), '9900')
  await user.type(screen.getByLabelText('SHA-256 of reviewed decision evidence'), 'a'.repeat(64))
  expect(button).toBeDisabled()
  await user.click(screen.getByRole('checkbox'))
  await user.click(button)
  expect(await screen.findByRole('status')).toHaveTextContent('Outcome unknown')
  expect(JSON.parse(fetcher.mock.calls[1][1].body)).toEqual({ source_kind: 'activation', source_id: 'local-grant', amount_minor: 9900, evidence_sha256: 'a'.repeat(64), authorize: true })
  expect(fetcher).toHaveBeenCalledTimes(2)
})
it('shows fresh sign-in requirement without exposing upstream errors', async () => {
  vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response('private-provider-error', { status: 403 })))
  renderWithProviders(<RefundOperatorCard />)
  expect(await screen.findByRole('alert')).toHaveTextContent('Sign in again')
  expect(screen.queryByText('private-provider-error')).not.toBeInTheDocument()
})
