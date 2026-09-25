import { useCallback, useEffect, useMemo, useState, type ReactNode } from 'react'
import { useQuery } from '@tanstack/react-query'
import '@/billing/billing.css'
import { FALLBACK_PRICING } from '@/billing/catalog'
import { fetchEntitlements, fetchFounderCampaign, fetchPricingCatalog } from '@/billing/api'
import type { Capability, Metric, UpgradeIntent } from '@/billing/types'
import { UpgradeDialog } from '@/components/upgrade-dialog'
import { useAuth } from '@/contexts/auth-context'
import { BillingContext } from '@/contexts/billing-context'

export function BillingProvider({ children }: { children: ReactNode }) {
  const { token, isLoading: authLoading } = useAuth()
  const [upgradeIntent, setUpgradeIntent] = useState<UpgradeIntent | null>(null)

  const catalogQuery = useQuery({
    queryKey: ['billing', 'catalog'],
    queryFn: fetchPricingCatalog,
    staleTime: 1000 * 60 * 60,
    retry: 1,
  })

  const founderCampaignQuery = useQuery({
    queryKey: ['billing', 'founder-campaign'],
    queryFn: fetchFounderCampaign,
    staleTime: 10_000,
    retry: 1,
    refetchInterval: (query) => query.state.data?.live ? 10_000 : false,
  })

  const entitlementsQuery = useQuery({
    queryKey: ['billing', 'entitlements', token ? 'signed-in' : 'guest'],
    queryFn: () => fetchEntitlements(token!),
    enabled: Boolean(token) && !authLoading,
    staleTime: 30_000,
    retry: 1,
  })

  const entitlements = token ? (entitlementsQuery.data ?? null) : null
  const plan = entitlements?.plan ?? 'free'

  useEffect(() => {
    document.documentElement.dataset.fincoPlan = plan
    return () => {
      delete document.documentElement.dataset.fincoPlan
    }
  }, [plan])

  const hasCapability = useCallback(
    (capability: Capability) => Boolean(entitlements?.capabilities?.[capability]),
    [entitlements],
  )
  const limit = useCallback(
    (metric: Metric) => entitlements?.limits?.[metric],
    [entitlements],
  )
  const usage = useCallback(
    (metric: Metric) => entitlements?.usage?.[metric],
    [entitlements],
  )
  const requestUpgrade = useCallback((intent: UpgradeIntent) => setUpgradeIntent(intent), [])

  const value = useMemo(
    () => ({
      catalog: catalogQuery.data ?? FALLBACK_PRICING,
      entitlements,
      founderCampaign: founderCampaignQuery.data ?? null,
      isLoading: authLoading || (Boolean(token) && entitlementsQuery.isLoading),
      plan,
      hasCapability,
      limit,
      usage,
      requestUpgrade,
      refreshEntitlements: entitlementsQuery.refetch,
      refreshFounderCampaign: founderCampaignQuery.refetch,
    }),
    [
      authLoading,
      catalogQuery.data,
      entitlements,
      entitlementsQuery.isLoading,
      founderCampaignQuery.data,
      founderCampaignQuery.refetch,
      entitlementsQuery.refetch,
      hasCapability,
      limit,
      plan,
      requestUpgrade,
      token,
      usage,
    ],
  )

  return (
    <BillingContext.Provider value={value}>
      {children}
      <UpgradeDialog intent={upgradeIntent} onOpenChange={(open) => !open && setUpgradeIntent(null)} />
    </BillingContext.Provider>
  )
}
