import { LockKeyhole } from 'lucide-react'
import { useBilling } from '@/contexts/billing-context'
import { CAPABILITY_PLAN } from '@/billing/catalog'
import type { Capability } from '@/billing/types'
import { PlanBadge } from '@/components/plan-badge'
import { Button } from '@/components/ui/button'
import { FinCoRouteLoader } from '@/transitions/finco-route-loader'

export function EntitlementRoute({
  capability,
  title,
  description,
  children,
}: {
  capability: Capability
  title: string
  description: string
  children: React.ReactNode
}) {
  const { hasCapability, isLoading, requestUpgrade } = useBilling()
  if (isLoading) return <FinCoRouteLoader />
  if (hasCapability(capability)) return <>{children}</>

  const plan = CAPABILITY_PLAN[capability]
  return (
    <div className="mx-auto flex min-h-[68vh] max-w-xl items-center justify-center px-4 py-10">
      <section className="w-full overflow-hidden rounded-[28px] border bg-card shadow-[0_24px_80px_rgba(0,0,0,.09)]">
        <div className="relative p-7 sm:p-9">
          <div className="pointer-events-none absolute inset-x-12 top-0 h-32 rounded-full bg-foreground/[0.045] blur-3xl" />
          <div className="relative">
            <div className="mb-5 flex items-center gap-2.5">
              <span className="grid size-11 place-items-center rounded-2xl border bg-muted/50 shadow-inner">
                <LockKeyhole className="size-5" />
              </span>
              <PlanBadge plan={plan} />
            </div>
            <h1 className="text-2xl font-semibold tracking-tight sm:text-3xl">{title}</h1>
            <p className="mt-2 max-w-md text-sm leading-6 text-muted-foreground">{description}</p>
            <Button
              className="mt-7 h-11 rounded-xl px-5"
              onClick={() => requestUpgrade({ plan, reason: description })}
            >
              View {plan.toUpperCase()}
            </Button>
          </div>
        </div>
        <div className="border-t bg-muted/20 px-7 py-4 text-xs leading-5 text-muted-foreground sm:px-9">
          Paid access is verified by FinCo-Pilot on the server. Browser changes cannot unlock this feature.
        </div>
      </section>
    </div>
  )
}
