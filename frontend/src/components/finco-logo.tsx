import { cn } from '@/lib/utils'

type FinCoLogoProps = {
  size?: number
  className?: string
  /**
   * `auto` inherits the surrounding theme color. `on-dark` and `on-light`
   * pin the supplied mark to white/black for branded artwork surfaces.
   */
  mode?: 'auto' | 'on-dark' | 'on-light'
}

/**
 * FinCo-Pilot F mark traced from the supplied production artwork.
 *
 * Keeping the mark as an inline vector means the same crop/geometry stays
 * razor-sharp from the 20px sidebar treatment through the oversized auth
 * artwork, while `currentColor` makes light/dark theming deterministic.
 */
export function FinCoLogo({ size = 24, className, mode = 'auto' }: FinCoLogoProps) {
  const fixedColor = mode === 'on-dark' ? '#FFFFFF' : mode === 'on-light' ? '#09090B' : undefined

  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 1000 1000"
      preserveAspectRatio="xMidYMid meet"
      className={cn('shrink-0', className)}
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      aria-hidden="true"
      style={fixedColor ? { color: fixedColor } : undefined}
    >
      <path
        fill="currentColor"
        d="M 882.6,70.0 L 307.9,71.0 L 279.4,77.1 L 261.1,83.2 L 230.5,97.5 L 197.9,119.9 L 175.5,141.3 L 151.0,172.9 L 129.6,214.7 L 121.5,242.2 L 116.4,274.8 L 117.4,929.0 L 161.2,923.9 L 186.7,914.7 L 207.0,903.5 L 236.6,879.1 L 247.8,865.8 L 263.1,841.4 L 274.3,811.8 L 279.4,779.2 L 279.4,644.7 L 281.4,628.4 L 287.5,607.0 L 296.7,588.6 L 310.0,570.3 L 330.3,550.9 L 343.6,541.8 L 364.0,531.6 L 387.4,524.5 L 401.7,522.4 L 627.9,522.4 L 653.4,521.4 L 673.7,516.3 L 684.9,510.2 L 696.1,501.0 L 804.2,367.5 L 425.1,366.5 L 397.6,370.6 L 365.0,383.8 L 344.6,398.1 L 328.3,414.4 L 261.1,495.9 L 260.0,308.4 L 266.1,281.9 L 280.4,257.5 L 293.7,244.2 L 306.9,235.1 L 329.3,225.9 L 347.7,222.8 L 723.7,222.8 L 743.0,218.8 L 765.4,207.6 L 784.8,189.2 Z"
      />
    </svg>
  )
}
