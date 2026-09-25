import { useMemo, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import {
  ArrowLeft,
  BarChart3,
  BriefcaseBusiness,
  Check,
  ChevronDown,
  Infinity as InfinityIcon,
  Lock,
  Sparkles,
  Upload,
  WalletCards,
  WandSparkles,
} from 'lucide-react'
import { toast } from 'sonner'
import { useAuth } from '@/contexts/auth-context'
import { useBilling } from '@/contexts/billing-context'
import { FinCoLogo } from '@/components/finco-logo'
import { PlanBadge } from '@/components/plan-badge'
import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'
import { formatInrMinor, priceFor } from '@/billing/catalog'
import { FounderOfferCard } from '@/billing/founder-offer-card'
import type { CheckoutOrder, PlanId } from '@/billing/types'
import type {
  RazorpayCheckoutOptions,
  RazorpayFailedResponse,
  RazorpaySuccessResponse,
} from '@/types/razorpay'

type PaidPlan = Exclude<PlanId, 'free'>
type Feature = {
  label: string
  detail?: string
  icon: React.ElementType
  minPlan?: PaidPlan
}

const FEATURES: Feature[] = [
  { label: 'Unlimited manual transactions', detail: 'Your financial history is never held behind a transaction quota.', icon: InfinityIcon },
  { label: 'Accounts, budgets & goals', detail: 'Free starts with 3 accounts, 2 active budgets and 2 active goals.', icon: WalletCards },
  { label: 'Statement imports', detail: '2/mo Free · 30/mo Pro · 200/mo Max.', icon: Upload },
  { label: 'Advanced financial reports', detail: 'Deeper net-worth, cash-flow and income/expense analysis.', icon: BarChart3, minPlan: 'pro' },
  { label: 'Smart rules & reconciliation', detail: 'Automate categorisation and resolve matching workflows.', icon: WandSparkles, minPlan: 'pro' },
  { label: 'Business workspaces & invoices', detail: 'Max unlocks business workspaces and up to 500 invoices/month.', icon: BriefcaseBusiness, minPlan: 'max' },
  { label: 'Advanced Agents & MCP automation', detail: 'Available on Max when the deployment capability is enabled.', icon: Sparkles, minPlan: 'max' },
]

const PLAN_COPY: Record<PlanId, { eyebrow: string; title: string; description: string }> = {
  free: {
    eyebrow: 'Start with confidence',
    title: 'Free',
    description: 'Everything needed to build a real money-tracking habit, with no ads and no card required.',
  },
  pro: {
    eyebrow: 'Most popular',
    title: 'Pro',
    description: 'For people who want deeper control, advanced analysis and powerful personal-finance automation.',
  },
  max: {
    eyebrow: 'Power tier',
    title: 'Max',
    description: 'For freelancers, creators and businesses that need workspaces, invoices and advanced automation.',
  },
}

const PLAN_LIMITS = [
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
  ['Attachment storage', '100 MB', '1 GB', '10 GB'],
  ['Advanced reports', 'Locked', 'Included', 'Included'],
  ['Business workspaces', 'Locked', 'Locked', 'Included'],
  ['Advanced Agents / MCP', 'Locked', 'Locked', 'Included*'],
] as const

const NETWORK_NODES = [
  [120, 18],
  [191, 53],
  [191, 127],
  [120, 162],
  [49, 127],
  [49, 53],
] as const

const NETWORK_EDGES = [
  [0, 1], [1, 2], [2, 3], [3, 4], [4, 5], [5, 0],
  [0, 3], [1, 4], [2, 5],
] as const

const NETWORK_FLOWS = [
  [0, 1], [1, 2], [2, 3], [3, 4], [4, 5], [5, 0],
  [0, 3], [2, 5], [4, 1],
] as const

function planAllows(selected: PlanId, minPlan?: PaidPlan) {
  if (!minPlan) return true
  if (minPlan === 'pro') return selected === 'pro' || selected === 'max'
  return selected === 'max'
}

function PricingHero() {
  return (
    <div className="relative mx-auto mb-3 grid h-40 w-60 place-items-center sm:h-44">
      <div className="absolute size-28 rounded-full border border-foreground/10 shadow-[inset_0_0_35px_rgba(128,128,128,.08)]" />
      <div className="absolute size-40 rounded-full border border-foreground/[0.06] shadow-[0_0_70px_rgba(128,128,128,.05)]" />

      <svg
        aria-hidden="true"
        viewBox="0 0 240 180"
        className="absolute h-[180px] w-[240px] overflow-visible text-foreground motion-safe:animate-[spin_22s_linear_infinite] motion-reduce:animate-none"
        style={{ transformOrigin: 'center' }}
      >
        <g fill="none" stroke="currentColor" strokeLinecap="round">
          {NETWORK_EDGES.map(([from, to], index) => {
            const [x1, y1] = NETWORK_NODES[from]
            const [x2, y2] = NETWORK_NODES[to]
            return (
              <line
                key={`${from}-${to}`}
                x1={x1}
                y1={y1}
                x2={x2}
                y2={y2}
                strokeWidth={index < 6 ? 0.8 : 0.55}
                opacity={index < 6 ? 0.14 : 0.08}
              />
            )
          })}
        </g>

        <g>
          {NETWORK_NODES.map(([x, y], index) => (
            <g key={`${x}-${y}`}>
              <circle cx={x} cy={y} r="7" fill="currentColor" opacity="0.035" />
              <circle
                cx={x}
                cy={y}
                r="3.1"
                fill="currentColor"
                opacity="0.62"
                className="motion-safe:animate-pulse"
                style={{ animationDelay: `${index * 180}ms` }}
              />
            </g>
          ))}
        </g>

        <g className="motion-reduce:hidden">
          {NETWORK_FLOWS.map(([from, to], index) => {
            const [x1, y1] = NETWORK_NODES[from]
            const [x2, y2] = NETWORK_NODES[to]
            return (
              <circle key={`flow-${from}-${to}`} r="2.15" fill="currentColor" opacity="0.9">
                <animateMotion
                  dur={`${0.92 + (index % 3) * 0.12}s`}
                  begin={`${index * 0.11}s`}
                  repeatCount="indefinite"
                  path={`M ${x1} ${y1} L ${x2} ${y2}`}
                />
              </circle>
            )
          })}
        </g>
      </svg>

      <div className="relative grid size-20 place-items-center rounded-[26px] border border-foreground/15 bg-background/88 shadow-[0_20px_55px_rgba(0,0,0,.16),0_0_34px_rgba(128,128,128,.08),inset_0_1px_0_rgba(255,255,255,.12)] backdrop-blur-xl [transform:perspective(500px)_rotateX(8deg)_rotateY(-8deg)] motion-safe:transition-transform motion-safe:duration-500 hover:[transform:perspective(500px)_rotateX(0deg)_rotateY(0deg)_scale(1.04)]">
        <FinCoLogo size={43} className="text-foreground" />
      </div>
    </div>
  )
}

function FeaturePanel({ plan }: { plan: PlanId }) {
  return (
    <div className="overflow-hidden rounded-[26px] border border-border/80 bg-card shadow-[0_18px_55px_rgba(0,0,0,.07)]">
      {FEATURES.map((feature, index) => {
        const allowed = planAllows(plan, feature.minPlan)
        const Icon = feature.icon
        return (
          <div
            key={feature.label}
            className={cn(
              'flex min-h-[62px] items-center gap-3 px-4 py-3.5 sm:min-h-[64px] sm:px-5',
              index !== 0 && 'sm:border-t sm:border-border/60',
              !allowed && 'text-muted-foreground sm:bg-muted/20',
            )}
          >
            <span className={cn('hidden size-8 shrink-0 place-items-center rounded-xl border bg-background/60 sm:grid', !allowed && 'opacity-60')}>
              {allowed ? <Icon className="size-4" /> : <Lock className="size-3.5" />}
            </span>
            <span className="min-w-0 flex-1">
              <span className="block text-sm font-medium text-foreground/95">{feature.label}</span>
              {feature.detail && <span className="mt-0.5 block text-xs leading-5 text-muted-foreground">{feature.detail}</span>}
            </span>
            {allowed ? (
              <Check className="size-4 shrink-0 text-foreground/70" />
            ) : feature.minPlan ? (
              <span className="flex shrink-0 items-center gap-2">
                <Lock className="size-3.5 sm:hidden" />
                <PlanBadge plan={feature.minPlan} compact />
              </span>
            ) : null}
          </div>
        )
      })}
    </div>
  )
}

function BillingSelector({
  plan,
  interval,
  onInterval,
}: {
  plan: PlanId
  interval: 'monthly' | 'annual'
  onInterval: (value: 'monthly' | 'annual') => void
}) {
  const { catalog, founderCampaign } = useBilling()
  if (plan === 'free') {
    return (
      <div className="rounded-[24px] border bg-card p-4 shadow-sm">
        <div className="text-sm text-muted-foreground">Free forever</div>
        <div className="mt-1 text-3xl font-semibold tracking-tight">₹0</div>
        <div className="mt-1 text-xs text-muted-foreground">No card required. No ads.</div>
      </div>
    )
  }

  if (plan === 'max') {
    const maxPrice = priceFor(catalog, 'max', 'monthly')
    return (
      <div className="rounded-[24px] border-2 border-foreground bg-card p-4 shadow-[0_10px_35px_rgba(0,0,0,.10)]">
        <div className="flex items-center justify-between gap-3">
          <div>
            <div className="text-sm text-muted-foreground">Monthly</div>
            <div className="mt-1 text-2xl font-semibold tracking-tight">{formatInrMinor(maxPrice?.amount_minor ?? 34_900)}<span className="text-sm font-normal text-muted-foreground"> / month</span></div>
          </div>
          <PlanBadge plan="max" />
        </div>
        <div className="mt-2 text-xs text-muted-foreground">Max annual is intentionally not offered in V1.</div>
      </div>
    )
  }

  const monthly = priceFor(catalog, 'pro', 'monthly')
  const annual = priceFor(catalog, 'pro', 'annual')
  const founderMonthly = founderCampaign?.live && founderCampaign.current_amount_minor != null
    ? founderCampaign.current_amount_minor
    : null
  const choices = [
    {
      key: 'monthly' as const,
      label: founderMonthly != null ? 'Founder monthly' : 'Monthly',
      price: formatInrMinor(founderMonthly ?? monthly?.amount_minor ?? 9_900),
      suffix: founderMonthly != null ? 'first 60 days · then ₹99/month' : '/ month',
    },
    { key: 'annual' as const, label: 'Annual', price: formatInrMinor(annual?.amount_minor ?? 99_900), suffix: '/ year' },
  ]
  return (
    <div className="grid grid-cols-2 overflow-hidden rounded-[24px] border bg-card shadow-sm">
      {choices.map((choice) => {
        const selected = interval === choice.key
        return (
          <button
            key={choice.key}
            type="button"
            onClick={() => onInterval(choice.key)}
            className={cn(
              'relative min-h-[118px] p-4 text-left transition',
              choice.key === 'annual' && 'border-l',
              selected ? 'z-10 rounded-[22px] border-2 border-foreground bg-background shadow-[0_8px_28px_rgba(0,0,0,.10)]' : 'text-muted-foreground',
            )}
          >
            <div className="flex items-center justify-between gap-2 text-sm">
              <span>{choice.label}</span>
              {choice.key === 'annual' && <span className="text-[11px] font-semibold text-foreground">Save {formatInrMinor(catalog.pro_annual_saving_minor)}</span>}
            </div>
            <div className={cn('mt-3 text-xl font-semibold tracking-tight', selected && 'text-foreground')}>{choice.price}</div>
            <div className="mt-1 text-xs">{choice.suffix}</div>
          </button>
        )
      })}
    </div>
  )
}

export default function PricingPage() {
  const navigate = useNavigate()
  const [params, setParams] = useSearchParams()
  const { user, token } = useAuth()
  const {
    catalog,
    founderCampaign,
    refreshFounderCampaign,
    plan: currentPlan,
    isLoading: billingLoading,
  } = useBilling()
  const requestedPlan = params.get('plan')
  const explicitPlan = requestedPlan === 'free' || requestedPlan === 'pro' || requestedPlan === 'max'
    ? requestedPlan as PlanId
    : null
  const selectedPlan: PlanId = explicitPlan ?? (user && !billingLoading ? currentPlan : 'pro')
  const [interval, setInterval] = useState<'monthly' | 'annual'>('monthly')

  const selectedPrice = useMemo(() => {
    if (selectedPlan === 'free') return priceFor(catalog, 'free', 'none')
    if (selectedPlan === 'max') return priceFor(catalog, 'max', 'monthly')
    return priceFor(catalog, 'pro', interval)
  }, [catalog, interval, selectedPlan])

  const selectPlan = (next: PlanId) => {
    const nextParams = new URLSearchParams(params)
    nextParams.set('plan', next)
    setParams(nextParams, { replace: true })
  }

  const continueWithPlan = async (plan: PlanId) => {
    if (user && currentPlan === plan) return
    selectPlan(plan)

    if (!user || !token) {
      navigate(plan === 'free' ? '/register' : '/login?next=' + encodeURIComponent('/pricing?plan=' + plan))
      return
    }

    if (plan === 'free') return

    const publicKey = import.meta.env.VITE_RAZORPAY_KEY_ID as string | undefined
    if (!publicKey) {
      toast.error('Payment checkout is not configured on this installation.')
      return
    }
    if (!window.Razorpay) {
      toast.error('Payment SDK failed to load. Please refresh the page and try again.')
      return
    }

    const effectiveInterval = plan === 'max' ? 'monthly' : interval
    const authHeaders = {
      'Content-Type': 'application/json',
      Authorization: 'Bearer ' + token,
    }

    try {
      const orderRes = await fetch('/api/checkout/create-order', {
        method: 'POST',
        headers: authHeaders,
        body: JSON.stringify({ plan, interval: effectiveInterval }),
      })

      if (!orderRes.ok) {
        const errData = await orderRes.json().catch(() => ({}))
        const detail = (errData as { detail?: string }).detail ?? 'Could not start checkout.'
        toast.error(detail)
        return
      }

      const orderData = await orderRes.json() as CheckoutOrder

      const cancelQuote = async () => {
        try {
          await fetch('/api/checkout/cancel-reservation', {
            method: 'POST',
            headers: authHeaders,
            body: JSON.stringify({ reservation_id: orderData.reservation_id }),
          })
          await refreshFounderCampaign()
        } catch {
          // Reservation expiry remains the server-side fallback if cancellation
          // cannot be delivered (for example, the browser went offline).
        }
      }

      const offerDescription = orderData.founder_wave != null
        ? 'Founder Wave ' + orderData.founder_wave + ' · ' + orderData.service_period_days + ' days Pro'
        : plan.toUpperCase() + ' · ' + orderData.service_period_days + '-day first period'

      const options: RazorpayCheckoutOptions = {
        key: publicKey,
        amount: orderData.amount,
        currency: orderData.currency,
        name: 'FinCo-Pilot',
        description: offerDescription,
        order_id: orderData.order_id,
        handler: async (response: RazorpaySuccessResponse) => {
          try {
            const verifyRes = await fetch('/api/checkout/verify-payment', {
              method: 'POST',
              headers: authHeaders,
              body: JSON.stringify({
                razorpay_payment_id: response.razorpay_payment_id,
                razorpay_order_id: response.razorpay_order_id,
                razorpay_signature: response.razorpay_signature,
              }),
            })
            if (verifyRes.ok) {
              await refreshFounderCampaign()
              toast.success('Payment captured and verified. Activation is pending the secure subscription lifecycle.')
            } else {
              const body = await verifyRes.json().catch(() => ({}))
              const detail = (body as { detail?: string }).detail
              toast.error(detail ?? 'Payment verification failed. Please contact support.')
            }
          } catch {
            toast.error('Could not verify payment. Please contact support.')
          }
        },
        modal: {
          ondismiss: () => {
            void cancelQuote()
            toast.info('Checkout was cancelled. Your temporary price hold was released.')
          },
        },
        theme: { color: '#000000' },
      }

      const rzp = new window.Razorpay(options)
      rzp.on('payment.failed', () => {
        toast.error('Payment failed. No paid entitlement was activated.')
      })
      rzp.open()
    } catch {
      toast.error('Could not connect to the payment service. Please try again.')
    }
  }

  const isCurrent = Boolean(user) && currentPlan === selectedPlan
  const paid = selectedPlan !== 'free'
  const taxCopy = catalog.tax_display_mode === 'inclusive'
    ? 'Prices include applicable taxes.'
    : catalog.tax_display_mode === 'exclusive'
      ? 'Applicable taxes may be added at checkout.'
      : 'Tax treatment is not configured; production paid checkout remains fail-closed.'
  const ctaLabel = isCurrent
    ? 'Current plan'
    : !user
      ? paid ? `Sign in for ${PLAN_COPY[selectedPlan].title}` : 'Start free'
      : selectedPlan === 'free'
        ? 'Downgrade to Free'
        : `Continue with ${PLAN_COPY[selectedPlan].title}`

  return (
    <main className="min-h-screen bg-background text-foreground [padding-bottom:max(2rem,env(safe-area-inset-bottom))]">
      <div className="mx-auto w-full max-w-6xl px-4 pb-16 pt-[max(1rem,env(safe-area-inset-top))] sm:px-6 lg:px-8">
        <header className="flex h-12 items-center justify-between">
          <button type="button" onClick={() => navigate(-1)} className="grid size-10 place-items-center rounded-full border bg-card transition hover:bg-muted" aria-label="Go back">
            <ArrowLeft className="size-4" />
          </button>
          <div className="flex items-center gap-2 text-sm font-semibold">
            <FinCoLogo size={22} className="text-foreground" />
            FinCo-Pilot
          </div>
          <div className="w-10" />
        </header>

        <section className="mx-auto max-w-2xl pb-5 pt-4 text-center sm:pt-7">
          <PricingHero />
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-muted-foreground">Simple pricing · serious control</p>
          <h1 className="mx-auto mt-3 max-w-xl text-3xl font-semibold leading-tight tracking-[-0.045em] sm:text-5xl">Choose how powerful you want FinCo-Pilot to be.</h1>
          <p className="mx-auto mt-3 max-w-lg text-sm leading-6 text-muted-foreground sm:text-base">Start free. Upgrade only when the extra power is worth it. Your existing financial history stays yours even after a downgrade.</p>
        </section>

        {selectedPlan === 'pro' && (
          <div className="mx-auto max-w-3xl">
            <FounderOfferCard campaign={founderCampaign} />
          </div>
        )}

        <section className="mx-auto max-w-xl lg:hidden">
          <div className="mb-5 grid grid-cols-3 gap-1 rounded-2xl bg-muted/45 p-1" role="tablist" aria-label="Plans">
            {(['free', 'pro', 'max'] as const).map((plan) => (
              <button
                key={plan}
                type="button"
                role="tab"
                aria-selected={selectedPlan === plan}
                onClick={() => selectPlan(plan)}
                className={cn(
                  'flex h-11 items-center justify-center rounded-xl text-sm font-semibold capitalize text-muted-foreground transition-[background-color,color,box-shadow,transform] duration-200',
                  selectedPlan === plan && 'bg-background text-foreground shadow-[0_5px_18px_rgba(0,0,0,.10)] ring-1 ring-border/70',
                )}
              >
                {PLAN_COPY[plan].title}
              </button>
            ))}
          </div>

          <div className="mb-4 px-1">
            <div className="text-[11px] font-semibold uppercase tracking-[0.16em] text-muted-foreground">{PLAN_COPY[selectedPlan].eyebrow}</div>
            <h2 className="mt-1 text-2xl font-semibold">{PLAN_COPY[selectedPlan].title}</h2>
            <p className="mt-1.5 text-sm leading-6 text-muted-foreground">{PLAN_COPY[selectedPlan].description}</p>
          </div>

          <FeaturePanel plan={selectedPlan} />
          <div className="mt-4"><BillingSelector plan={selectedPlan} interval={interval} onInterval={setInterval} /></div>
          <Button disabled={isCurrent} onClick={() => continueWithPlan(selectedPlan)} className="mt-4 h-14 w-full rounded-[22px] text-base font-semibold shadow-lg">{ctaLabel}</Button>
          {paid && selectedPrice && (
            <p className="mt-2 text-center text-xs leading-5 text-muted-foreground">
              The server locks your exact eligible offer before Razorpay opens. {taxCopy}
            </p>
          )}
        </section>

        <section className="hidden gap-4 lg:grid lg:grid-cols-3">
          {(['free', 'pro', 'max'] as const).map((plan) => {
            const isPro = plan === 'pro'
            const isSelected = selectedPlan === plan
            const founderPro = plan === 'pro' && founderCampaign?.live && founderCampaign.current_amount_minor != null
            const price = plan === 'free'
              ? priceFor(catalog, 'free', 'none')
              : plan === 'pro'
                ? founderPro
                  ? { amount_minor: founderCampaign.current_amount_minor }
                  : priceFor(catalog, 'pro', 'monthly')
                : priceFor(catalog, 'max', 'monthly')
            return (
              <article key={plan} className={cn('relative flex flex-col rounded-[30px] border bg-card p-6 shadow-sm transition', isPro && 'border-foreground/40 shadow-[0_22px_70px_rgba(0,0,0,.10)]', isSelected && 'ring-1 ring-foreground/25')}>
                {isPro && <div className="absolute -top-3 left-1/2 -translate-x-1/2 rounded-full border bg-background px-3 py-1 text-[10px] font-bold uppercase tracking-[0.14em]">Most popular</div>}
                <div className="flex items-center justify-between gap-3">
                  <div><div className="text-sm text-muted-foreground">{PLAN_COPY[plan].eyebrow}</div><h2 className="mt-1 text-2xl font-semibold">{PLAN_COPY[plan].title}</h2></div>
                  {plan !== 'free' && <PlanBadge plan={plan} />}
                </div>
                <div className="mt-5 text-4xl font-semibold tracking-tight">{formatInrMinor(price?.amount_minor ?? 0)}</div>
                <div className="mt-1 text-xs leading-5 text-muted-foreground">
                  {plan === 'free'
                    ? 'forever'
                    : plan === 'pro'
                      ? founderPro
                        ? 'eligible founders · first 60 days · then ₹99/month'
                        : 'per month · ₹999/year also available'
                      : 'eligible first monthly purchase gets 60 days · then ₹349/month'}
                </div>
                <p className="mt-4 min-h-16 text-sm leading-6 text-muted-foreground">{PLAN_COPY[plan].description}</p>
                <Button variant={isPro ? 'default' : 'outline'} className="mt-4 h-11 rounded-xl" onClick={() => continueWithPlan(plan)} disabled={Boolean(user) && currentPlan === plan}>{Boolean(user) && currentPlan === plan ? 'Current plan' : plan === 'free' ? 'Choose Free' : `Choose ${PLAN_COPY[plan].title}`}</Button>
                <div className="mt-5 space-y-3 border-t pt-5">
                  {FEATURES.slice(0, 6).map((feature) => {
                    const allowed = planAllows(plan, feature.minPlan)
                    return <div key={feature.label} className={cn('flex items-start gap-2.5 text-sm', !allowed && 'text-muted-foreground')}>
                      {allowed ? <Check className="mt-0.5 size-4 shrink-0" /> : <Lock className="mt-0.5 size-4 shrink-0" />}
                      <span className="flex-1">{feature.label}</span>
                      {!allowed && feature.minPlan && <PlanBadge plan={feature.minPlan} compact />}
                    </div>
                  })}
                </div>
              </article>
            )
          })}
        </section>


        <section className="mx-auto mt-14 max-w-5xl">
          <div className="text-center"><p className="text-xs font-semibold uppercase tracking-[0.16em] text-muted-foreground">Compare plans</p><h2 className="mt-2 text-2xl font-semibold sm:text-3xl">Clear limits. No surprise locks.</h2></div>
          <div className="mt-6 overflow-hidden rounded-[28px] border bg-card">
            <div className="overflow-x-auto">
              <table className="w-full min-w-[680px] text-sm">
                <thead className="bg-muted/35"><tr><th className="p-4 text-left font-medium">Feature</th><th className="p-4 text-center font-medium">Free</th><th className="p-4 text-center font-medium"><span className="inline-flex items-center gap-2">Pro <PlanBadge plan="pro" compact /></span></th><th className="p-4 text-center font-medium"><span className="inline-flex items-center gap-2">Max <PlanBadge plan="max" compact /></span></th></tr></thead>
                <tbody>{PLAN_LIMITS.map(([label, free, pro, max]) => <tr key={label} className="border-t"><td className="p-4 font-medium">{label}</td>{[free, pro, max].map((value, i) => <td key={i} className="p-4 text-center text-muted-foreground">{value === 'Locked' ? <span className="inline-flex items-center gap-1.5"><Lock className="size-3" /> Locked</span> : value}</td>)}</tr>)}</tbody>
              </table>
            </div>
          </div>
          <p className="mt-2 text-xs text-muted-foreground">* Advanced Agents/MCP also require the deployment capability to be enabled.</p>
        </section>

        <section className="mx-auto mt-12 max-w-3xl">
          <h2 className="text-center text-2xl font-semibold">Pricing questions</h2>
          <div className="mt-5 divide-y rounded-[26px] border bg-card px-5 sm:px-6">
            {[
              ['Will my data disappear if I cancel?', 'No. FinCo keeps existing financial records readable. If you are above a lower-plan limit, creation is blocked until you reduce usage or upgrade.'],
              ['How does the founder price work?', 'Eligible new Pro Monthly buyers get the current server-confirmed founder wave price for the first 60 days from public launch. It then returns to the standard ₹99/month price. Founder eligibility and remaining capacity are verified by the backend, not the browser.'],
              ['Can the price change while I am paying?', 'No. Starting checkout creates a short-lived server-side reservation that locks the exact offer shown for that checkout window.'],
              ['Why is there no Max annual plan?', 'Because it is not part of V1. We show only real prices that are actually approved instead of inventing a disabled or crossed-out annual number.'],
              ['Does Free show ads?', 'No. FinCo-Pilot pricing is designed without advertising inside the finance experience.'],
            ].map(([question, answer]) => (
              <details key={question} className="group py-4"><summary className="flex cursor-pointer list-none items-center justify-between gap-4 font-medium"><span>{question}</span><ChevronDown className="size-4 shrink-0 transition group-open:rotate-180" /></summary><p className="pr-8 pt-2 text-sm leading-6 text-muted-foreground">{answer}</p></details>
            ))}
          </div>
        </section>

        <footer className="mx-auto mt-12 max-w-xl text-center text-xs leading-5 text-muted-foreground">
          Prices shown in INR. The backend confirms the exact offer before checkout. {taxCopy}
        </footer>
      </div>
    </main>
  )
}
