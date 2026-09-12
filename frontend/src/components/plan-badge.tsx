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
  const isPro = plan === 'pro'

  return (
    <span
      aria-label={`${label} plan`}
      data-plan={plan}
      className={cn(
        'relative inline-flex shrink-0 items-center justify-center gap-1 overflow-hidden rounded-full text-white',
        'before:absolute before:inset-x-1 before:top-px before:h-px before:rounded-full before:bg-white/35',
        'motion-safe:transition-[transform,filter,box-shadow] motion-safe:duration-200 motion-safe:hover:-translate-y-px',
        isPro
          ? [
              'border border-violet-300/35 bg-gradient-to-b from-violet-500 via-violet-600 to-purple-800 font-bold',
              'shadow-[0_5px_16px_rgba(124,58,237,.38),inset_0_1px_0_rgba(255,255,255,.28),inset_0_-1px_0_rgba(46,16,101,.45)]',
              'motion-safe:hover:shadow-[0_7px_20px_rgba(124,58,237,.48),inset_0_1px_0_rgba(255,255,255,.32)]',
            ]
          : [
              'border border-white/16 bg-gradient-to-br from-zinc-700 via-zinc-950 to-black font-extrabold',
              'shadow-[0_5px_16px_rgba(0,0,0,.38),inset_0_1px_0_rgba(255,255,255,.20),inset_0_-1px_0_rgba(0,0,0,.72)]',
              'motion-safe:hover:shadow-[0_8px_22px_rgba(0,0,0,.48),inset_0_1px_0_rgba(255,255,255,.24)]',
            ],
        compact
          ? 'h-[18px] px-1.5 text-[8px] tracking-[0.14em]'
          : 'h-5 px-2 text-[9px] tracking-[0.16em]',
        className,
      )}
    >
      <Icon className={cn('relative z-10', compact ? 'size-2.5' : 'size-3')} strokeWidth={2.3} />
      <span className="relative z-10">{label}</span>
    </span>
  )
}
