import { Lock } from 'lucide-react'
import { PlanBadge } from '@/components/plan-badge'
import { cn } from '@/lib/utils'
import type { UpgradeIntent } from '@/billing/types'
import { useBilling } from '@/contexts/billing-context'

export function LockedFeature({
  plan,
  reason,
  children,
  className,
}: {
  plan: UpgradeIntent['plan']
  reason: string
  children: React.ReactNode
  className?: string
}) {
  const { requestUpgrade } = useBilling()
  return (
    <button
      type="button"
      aria-disabled="true"
      onClick={() => requestUpgrade({ plan, reason })}
      className={cn(
        'group flex w-full items-center gap-3 rounded-xl border border-border/70 bg-muted/30 px-3.5 py-3 text-left',
        'text-muted-foreground transition hover:border-foreground/20 hover:bg-muted/50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring',
        className,
      )}
    >
      <span className="grid size-8 shrink-0 place-items-center rounded-xl border bg-background/70 shadow-sm">
        <Lock className="size-3.5" />
      </span>
      <span className="min-w-0 flex-1 text-sm">{children}</span>
      <PlanBadge plan={plan} compact />
    </button>
  )
}
