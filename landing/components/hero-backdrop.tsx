'use client'

import dynamic from 'next/dynamic'
import { useMediaQuery } from '@/hooks/use-media-query'

const ProximityGrid = dynamic(() => import('@/components/spaceui/proximity-grid').then(module => module.ProximityGrid), { ssr: false })

/** Optional source-adopted decoration; mobile never loads grid motion work. */
export function HeroBackdrop() {
  const desktopPointer = useMediaQuery('(min-width: 921px) and (pointer: fine)')
  const reduced = useMediaQuery('(prefers-reduced-motion: reduce)', true)
  return <div className="hero-ambient" aria-hidden="true">{desktopPointer && !reduced ? <ProximityGrid cellSize={86} gap={2} proximity={3} interactive={false}/> : null}</div>
}
