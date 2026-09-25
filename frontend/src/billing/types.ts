export type PlanId = 'free' | 'pro' | 'max'
export type BillingInterval = 'none' | 'monthly' | 'annual'
export type SubscriptionStatus = 'free' | 'active' | 'grace' | 'past_due' | 'canceled' | 'expired'

export type Capability =
  | 'advanced_reports'
  | 'rules'
  | 'smart_reconciliation'
  | 'business_workspaces'
  | 'invoices'
  | 'agents_automation'

export type Metric =
  | 'total_workspaces'
  | 'personal_workspaces'
  | 'business_workspaces'
  | 'accounts'
  | 'active_budgets'
  | 'active_goals'
  | 'active_recurring'
  | 'assets'
  | 'imports_monthly'
  | 'rules'
  | 'active_split_groups'
  | 'group_members'
  | 'invoices_monthly'
  | 'ai_actions_monthly'
  | 'storage_bytes'

export interface PriceOption {
  plan: PlanId
  interval: BillingInterval
  amount_minor: number
  currency: string
}

export type TaxDisplayMode = 'unconfigured' | 'inclusive' | 'exclusive'

export interface PricingCatalog {
  prices: PriceOption[]
  pro_annual_saving_minor: number
  tax_display_mode: TaxDisplayMode
}

export interface FounderWaveStatus {
  wave: number
  capacity: number
  claimed: number
  held: number
  available: number
  amount_minor: number
  next_amount_minor: number
  currency: 'INR'
}

export interface FounderCampaignStatus {
  code: string
  catalog_version: string
  state: 'scheduled' | 'active' | 'paused' | 'closed'
  version: number
  live: boolean
  presale_starts_at: string | null
  presale_ends_at: string | null
  public_launch_at: string | null
  current_wave: number | null
  current_amount_minor: number | null
  next_amount_minor: number | null
  intro_service_days: number
  total_capacity: number
  total_claimed: number
  total_held: number
  total_available: number
  waves: FounderWaveStatus[]
}

export interface CheckoutOrder {
  order_id: string
  amount: number
  currency: string
  plan: PlanId
  interval: BillingInterval
  reservation_id: string
  offer_code: string
  founder_wave: number | null
  founder_position: number | null
  renewal_amount_minor: number
  renewal_interval: BillingInterval
  service_period_days: number
  service_starts_at: string | null
  reservation_expires_at: string
}

export interface Entitlements {
  plan: PlanId
  status: SubscriptionStatus
  billing_interval: BillingInterval
  current_period_end: string | null
  cancel_at_period_end: boolean
  capabilities: Record<Capability, boolean>
  limits: Record<Metric, number>
  usage: Partial<Record<Metric, number>>
  resets_at: Partial<Record<Metric, string | null>>
}

export interface UpgradeIntent {
  plan: Exclude<PlanId, 'free'>
  reason?: string
}
