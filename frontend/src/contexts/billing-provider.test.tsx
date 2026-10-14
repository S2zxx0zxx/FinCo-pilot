import { beforeEach, describe, expect, it, vi } from 'vitest'
import { screen, waitFor } from '@testing-library/react'
import { useNavigate } from 'react-router-dom'
import { BillingProvider } from './billing-provider'
import { useBilling } from './billing-context'
import { renderWithProviders } from '@/test/utils'
import { FALLBACK_PRICING } from '@/billing/catalog'

const mocks = vi.hoisted(() => ({ catalog: vi.fn(), campaign: vi.fn(), entitlements: vi.fn(), token: null as string | null }))
vi.mock('@/billing/api', () => ({ fetchPricingCatalog: mocks.catalog, fetchFounderCampaign: mocks.campaign, fetchEntitlements: mocks.entitlements }))
vi.mock('@/contexts/auth-context', () => ({ useAuth: () => ({ token: mocks.token, isLoading: false }) }))

function Consumer() {
  const billing = useBilling()
  const navigate = useNavigate()
  return <><button onClick={() => navigate('/pricing')}>Pricing</button><button onClick={() => billing.requestUpgrade({ plan: 'pro' })}>Upgrade</button></>
}

beforeEach(() => {
  vi.clearAllMocks()
  mocks.token = null
  mocks.catalog.mockResolvedValue(FALLBACK_PRICING)
  mocks.campaign.mockResolvedValue(null)
  mocks.entitlements.mockResolvedValue(null)
})

describe('billing demand loading', () => {
  it('does not fetch billing for anonymous login, then loads it on pricing navigation', async () => {
    const { user } = renderWithProviders(<BillingProvider><Consumer /></BillingProvider>, { route: '/login' })
    expect(mocks.catalog).not.toHaveBeenCalled()
    expect(mocks.campaign).not.toHaveBeenCalled()
    expect(mocks.entitlements).not.toHaveBeenCalled()
    await user.click(screen.getByRole('button', { name: 'Pricing' }))
    await waitFor(() => expect(mocks.catalog).toHaveBeenCalledTimes(1))
    expect(mocks.campaign).toHaveBeenCalledTimes(1)
    expect(mocks.entitlements).not.toHaveBeenCalled()
  })

  it('retains authenticated entitlements and the real upgrade dialog/open-close flow', async () => {
    mocks.token = 'synthetic-test-session'
    const { user } = renderWithProviders(<BillingProvider><Consumer /></BillingProvider>)
    await waitFor(() => expect(mocks.entitlements).toHaveBeenCalledWith(mocks.token))
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Upgrade' }))
    expect(await screen.findByRole('dialog')).toHaveTextContent('Unlock FinCo Pro')
    await user.keyboard('{Escape}')
    await waitFor(() => expect(screen.queryByRole('dialog')).not.toBeInTheDocument())
    await user.click(screen.getByRole('button', { name: 'Upgrade' }))
    expect(await screen.findByRole('dialog')).toHaveTextContent('Unlock FinCo Pro')
  })
})
