import { createContext, useContext } from 'react'
import type { Capability, Entitlements, Metric, PlanId, PricingCatalog, UpgradeIntent } from '@/billing/types'

export interface BillingContextValue {
  catalog: PricingCatalog
  entitlements: Entitlements | null
  isLoading: boolean
  plan: PlanId
  hasCapability: (capability: Capability) => boolean
  limit: (metric: Metric) => number | undefined
  usage: (metric: Metric) => number | undefined
  requestUpgrade: (intent: UpgradeIntent) => void
  refreshEntitlements: () => Promise<unknown>
}

export const BillingContext = createContext<BillingContextValue | null>(null)

export function useBilling() {
  const value = useContext(BillingContext)
  if (!value) throw new Error('useBilling must be used within BillingProvider')
  return value
}
