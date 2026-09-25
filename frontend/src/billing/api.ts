import type { Entitlements, FounderCampaignStatus, PricingCatalog } from '@/billing/types'

async function parseJson<T>(response: Response): Promise<T> {
  if (!response.ok) {
    let detail = `Request failed (${response.status})`
    try {
      const body = await response.json()
      if (typeof body?.detail === 'string') detail = body.detail
    } catch {
      // Keep the stable status fallback when a proxy returns non-JSON.
    }
    throw new Error(detail)
  }
  return response.json() as Promise<T>
}

export async function fetchPricingCatalog(): Promise<PricingCatalog> {
  return parseJson<PricingCatalog>(
    await fetch('/api/billing/catalog', {
      headers: { Accept: 'application/json' },
      credentials: 'same-origin',
    }),
  )
}

export async function fetchFounderCampaign(): Promise<FounderCampaignStatus> {
  return parseJson<FounderCampaignStatus>(
    await fetch('/api/billing/founder-campaign', {
      headers: { Accept: 'application/json' },
      credentials: 'same-origin',
    }),
  )
}

export async function fetchEntitlements(token: string): Promise<Entitlements> {
  return parseJson<Entitlements>(
    await fetch('/api/billing/entitlements', {
      headers: {
        Accept: 'application/json',
        Authorization: `Bearer ${token}`,
      },
      credentials: 'same-origin',
    }),
  )
}
