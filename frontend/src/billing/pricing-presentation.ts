import type { PlanId } from '@/billing/types'
import { Infinity as InfinityIcon, WalletCards, Upload, BarChart3, WandSparkles, BriefcaseBusiness, Sparkles } from 'lucide-react'
type PaidPlan = Exclude<PlanId, 'free'>
type Feature = {
  label: string
  detail?: string
  icon: React.ElementType
  minPlan?: PaidPlan
}

export const FEATURES: Feature[] = [
  { label: 'Unlimited manual transactions', detail: 'Your financial history is never held behind a transaction quota.', icon: InfinityIcon },
  { label: 'Accounts, budgets & goals', detail: 'Free starts with 3 accounts, 2 active budgets and 2 active goals.', icon: WalletCards },
  { label: 'Statement imports', detail: '2/mo Free · 30/mo Pro · 200/mo Max.', icon: Upload },
  { label: 'Advanced financial reports', detail: 'Deeper net-worth, cash-flow and income/expense analysis.', icon: BarChart3, minPlan: 'pro' },
  { label: 'Smart rules & reconciliation', detail: 'Automate categorisation and resolve matching workflows.', icon: WandSparkles, minPlan: 'pro' },
  { label: 'Business workspaces & invoices', detail: 'Max unlocks business workspaces and up to 500 invoices/month.', icon: BriefcaseBusiness, minPlan: 'max' },
  { label: 'Advanced Agents & MCP automation', detail: 'Available on Max when the deployment capability is enabled.', icon: Sparkles, minPlan: 'max' },
]

export const PLAN_COPY: Record<PlanId, { eyebrow: string; title: string; description: string }> = {
  free: {
    eyebrow: 'Start with confidence',
    title: 'Free',
    description: 'Everything needed to build a real money-tracking habit, with no ads and no card required.',
  },
  pro: {
    eyebrow: 'Deeper analysis',
    title: 'Pro',
    description: 'For people who want deeper control, advanced analysis and powerful personal-finance automation.',
  },
  max: {
    eyebrow: 'Power tier',
    title: 'Max',
    description: 'For freelancers, creators and businesses that need workspaces, invoices and advanced automation.',
  },
}

export const PLAN_LIMITS = [
  ['Total workspaces', '1', '1', '3'],
  ['Personal workspaces', '1', '1', '3'],
  ['Business workspaces', '0', '0', '3'],
  ['Accounts', '3', '25', '100'],
  ['Active budgets', '2', '25', '100'],
  ['Active goals', '2', '25', '100'],
  ['Recurring items', '3', '50', '250'],
  ['Assets / holdings', '3', '50', '500'],
  ['Imports / month', '2', '30', '200'],
  ['Smart rules', 'Locked', '25', '200'],
  ['Split groups', '1', '10', '50'],
  ['Members / group', '5', '15', '50'],
  ['Invoices / month', 'Locked', 'Locked', '500'],
  ['AI actions / month', '0', '0', '300*'],
  ['Attachment storage', '100 MiB', '1 GiB', '10 GiB'],
  ['Advanced reports', 'Locked', 'Included', 'Included'],
  ['Advanced Agents / MCP', 'Locked', 'Locked', 'Included*'],
] as const

export function planAllows(selected: PlanId, minPlan?: PaidPlan) {
  if (!minPlan) return true
  if (minPlan === 'pro') return selected === 'pro' || selected === 'max'
  return selected === 'max'
}
