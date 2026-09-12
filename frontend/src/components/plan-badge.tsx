import { Crown, Sparkles } from 'lucide-react'
import { cn } from '@/lib/utils'
import type { PlanId } from '@/billing/types'

export function PlanBadge({
  plan,
  className,
  compact = false,
}: {
  plan: Exclude<PlanId, 'free'>
  className?: string
  compact?: boolean
}) {
  const Icon = plan === 'max' ? Crown : Sparkles
  const label = plan.toUpperCase()
  return (
    <span
      aria-label={`${label} plan`}
      className={cn(
        'relative inline-flex shrink-0 items-center justify-center gap-1 overflow-hidden rounded-full',
        'border border-white/15 bg-zinc-950 text-white dark:border-white/20',
        'shadow-[0_5px_14px_rgba(0,0,0,.28),inset_0_1px_0_rgba(255,255,255,.18),inset_0_-1px_0_rgba(255,255,255,.04)]',
        'before:absolute before:inset-x-1 before:top-px before:h-px before:rounded-full before:bg-white/30',
        'motion-safe:transition-[transform,box-shadow] motion-safe:duration-200 motion-safe:hover:-translate-y-px',
        compact ? 'h-[18px] px-1.5 text-[8px] font-bold tracking-[0.14em]' : 'h-5 px-2 text-[9px] font-bold tracking-[0.16em]',
        className,
      )}
    >
      <Icon className={cn('relative z-10', compact ? 'size-2.5' : 'size-3')} strokeWidth={2.2} />
      <span className="relative z-10">{label}</span>
    </span>
  )
}
