import { describe, expect, it } from 'vitest'
import { screen } from '@testing-library/react'
import { FounderOfferCard } from '@/billing/founder-offer-card'
import type { FounderCampaignStatus } from '@/billing/types'
import { renderWithProviders } from '@/test/utils'

const liveCampaign: FounderCampaignStatus = {
  code: 'founder_v1',
  catalog_version: 'v1',
  state: 'active',
  version: 2,
  live: true,
  presale_starts_at: '2026-09-25T00:00:00Z',
  presale_ends_at: '2026-10-01T00:00:00Z',
  public_launch_at: '2026-10-01T00:00:00Z',
  current_wave: 1,
  current_amount_minor: 1_900,
  next_amount_minor: 4_900,
  intro_service_days: 60,
  total_capacity: 25_000,
  total_claimed: 4_321,
  total_held: 10,
  total_available: 20_669,
  waves: [
    {
      wave: 1,
      capacity: 5_000,
      claimed: 4_321,
      held: 10,
      available: 669,
      amount_minor: 1_900,
      next_amount_minor: 4_900,
      currency: 'INR',
    },
    {
      wave: 2,
      capacity: 20_000,
      claimed: 0,
      held: 0,
      available: 20_000,
      amount_minor: 4_900,
      next_amount_minor: 9_900,
      currency: 'INR',
    },
  ],
}

describe('FounderOfferCard', () => {
  it('renders only real server-supplied scarcity numbers and renewal disclosure', () => {
    renderWithProviders(<FounderOfferCard campaign={liveCampaign} />)

    expect(screen.getByLabelText('Founder Wave 1 offer')).toHaveTextContent('₹19')
    expect(screen.getByText('4,321 verified')).toBeInTheDocument()
    expect(screen.getByText('10 temporarily held')).toBeInTheDocument()
    expect(screen.getByText('669 available')).toBeInTheDocument()
    expect(screen.getByText(/then the standard Pro price is ₹99\/month/)).toBeInTheDocument()
    expect(screen.getByText(/Next price/)).toHaveTextContent('₹49')
  })

  it('does not invent scarcity when the campaign is not live', () => {
    renderWithProviders(
      <FounderOfferCard campaign={{ ...liveCampaign, live: false, state: 'paused' }} />,
    )
    expect(screen.queryByText(/Founding access/)).not.toBeInTheDocument()
  })
})
