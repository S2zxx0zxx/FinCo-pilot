import { cn } from '@/lib/utils'

type FinCoLogoProps = {
  size?: number
  className?: string
  /**
   * `auto` follows the application theme. `on-dark` and `on-light` are for
   * branded surfaces whose background is intentionally independent of the
   * current app theme (for example the always-dark auth artwork panel).
   */
  mode?: 'auto' | 'on-dark' | 'on-light'
}

/** FinCo-Pilot F mark, derived from the supplied production brand artwork. */
export function FinCoLogo({ size = 24, className, mode = 'auto' }: FinCoLogoProps) {
  const common = 'h-full w-full object-contain select-none'

  return (
    <span
      className={cn('inline-flex shrink-0 items-center justify-center', className)}
      style={{ width: size, height: size }}
      aria-hidden="true"
    >
      {mode === 'on-dark' ? (
        <img src="/brand/finco-mark-dark.png" alt="" className={common} draggable={false} />
      ) : mode === 'on-light' ? (
        <img src="/brand/finco-mark-light.png" alt="" className={common} draggable={false} />
      ) : (
        <>
          <img
            src="/brand/finco-mark-light.png"
            alt=""
            className={cn(common, 'dark:hidden')}
            draggable={false}
          />
          <img
            src="/brand/finco-mark-dark.png"
            alt=""
            className={cn(common, 'hidden dark:block')}
            draggable={false}
          />
        </>
      )}
    </span>
  )
}
