import type { Capability, Metric, PlanId, PricingCatalog } from '@/billing/types'

export const FALLBACK_PRICING: PricingCatalog = {
  prices: [
    { plan: 'free', interval: 'none', amount_minor: 0, currency: 'INR' },
    { plan: 'pro', interval: 'monthly', amount_minor: 9_900, currency: 'INR' },
    { plan: 'pro', interval: 'annual', amount_minor: 99_900, currency: 'INR' },
    { plan: 'max', interval: 'monthly', amount_minor: 34_900, currency: 'INR' },
  ],
  pro_annual_saving_minor: 18_900,
}

export const PLAN_RANK: Record<PlanId, number> = { free: 0, pro: 1, max: 2 }

export const CAPABILITY_PLAN: Record<Capability, Exclude<PlanId, 'free'>> = {
  advanced_reports: 'pro',
  rules: 'pro',
  smart_reconciliation: 'pro',
  business_workspaces: 'max',
  invoices: 'max',
  agents_automation: 'max',
}

export const METRIC_LABELS: Record<Metric, string> = {
  total_workspaces: 'Workspaces',
  personal_workspaces: 'Personal workspaces',
  business_workspaces: 'Business workspaces',
  accounts: 'Accounts',
  active_budgets: 'Active budgets',
  active_goals: 'Active goals',
  active_recurring: 'Recurring items',
  assets: 'Assets & holdings',
  imports_monthly: 'Statement imports / month',
  rules: 'Smart rules',
  active_split_groups: 'Active split groups',
  group_members: 'Members / split group',
  invoices_monthly: 'Invoices / month',
  ai_actions_monthly: 'AI actions / month',
  storage_bytes: 'Attachment storage',
}

export function formatInrMinor(amountMinor: number): string {
  return new Intl.NumberFormat('en-IN', {
    style: 'currency',
    currency: 'INR',
    maximumFractionDigits: 0,
  }).format(amountMinor / 100)
}

export function priceFor(
  catalog: PricingCatalog,
  plan: PlanId,
  interval: 'none' | 'monthly' | 'annual',
) {
  return catalog.prices.find((option) => option.plan === plan && option.interval === interval)
}

export function requiredPlanForCapability(capability: Capability) {
  return CAPABILITY_PLAN[capability]
}
