import { Squishmoji } from '@usespaceui/squishmoji/react'
import { useMediaQuery } from '@/hooks/spaceui/use-media-query'
import { cn } from '@/lib/utils'

/** Procedural and local: no identity is sent to a remote avatar service. */
export function IdentityAvatar({ seed, size = 32, className }: { seed: string; size?: number; className?: string }) {
  const reducedMotion = useMediaQuery('(prefers-reduced-motion: reduce)')
  return <span aria-hidden="true" className={cn('finco-identity inline-flex shrink-0 overflow-hidden rounded-xl bg-muted', className)}>
    <Squishmoji seed={seed} size={size} shape="squircle" expression="happy" backgroundStyle="solid"
      animate={false} animOnHover={!reducedMotion} animOnClick={false} className="size-full" />
  </span>
}
