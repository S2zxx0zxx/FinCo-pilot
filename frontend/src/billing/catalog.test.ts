import { describe, expect, it } from 'vitest'
import { FALLBACK_PRICING, formatInrMinor, priceFor } from '@/billing/catalog'

describe('pricing catalog', () => {
  it('matches the approved launch prices exactly', () => {
    expect(priceFor(FALLBACK_PRICING, 'free', 'none')?.amount_minor).toBe(0)
    expect(priceFor(FALLBACK_PRICING, 'pro', 'monthly')?.amount_minor).toBe(9_900)
    expect(priceFor(FALLBACK_PRICING, 'pro', 'annual')?.amount_minor).toBe(99_900)
    expect(priceFor(FALLBACK_PRICING, 'max', 'monthly')?.amount_minor).toBe(34_900)
    expect(priceFor(FALLBACK_PRICING, 'max', 'annual')).toBeUndefined()
  })

  it('keeps annual savings computed from the locked amounts', () => {
    const monthly = priceFor(FALLBACK_PRICING, 'pro', 'monthly')!.amount_minor
    const annual = priceFor(FALLBACK_PRICING, 'pro', 'annual')!.amount_minor
    expect(monthly * 12 - annual).toBe(FALLBACK_PRICING.pro_annual_saving_minor)
    expect(FALLBACK_PRICING.pro_annual_saving_minor).toBe(18_900)
  })

  it('formats INR without fake paise for the pricing surface', () => {
    expect(formatInrMinor(9_900)).toContain('99')
    expect(formatInrMinor(99_900)).toContain('999')
  })
})
