import { useEffect, useMemo, useState } from 'react'
import { useLocation } from 'react-router-dom'
import { FinCoLogo } from '@/components/finco-logo'
import { routeDestinationLabel } from '@/transitions/route-labels'

export function FinCoLoaderVisual({
  destination,
  leaving = false,
}: {
  destination: string
  leaving?: boolean
}) {
  return (
    <div
      className={`finco-route-loader${leaving ? ' finco-route-loader--leaving' : ''}`}
      role="status"
      aria-live="polite"
      aria-label={`Opening ${destination}`}
    >
      <div className="finco-route-loader__scene" aria-hidden="true">
        <div className="finco-route-loader__orbit finco-route-loader__orbit--outer" />
        <div className="finco-route-loader__orbit finco-route-loader__orbit--inner" />
        <div className="finco-route-loader__halo" />
        <div className="finco-route-loader__logo">
          <FinCoLogo size={68} />
        </div>
      </div>
      <div className="finco-route-loader__copy">
        <span className="finco-route-loader__brand">FinCo-Pilot</span>
        <span className="finco-route-loader__destination">Preparing {destination}</span>
      </div>
      <div className="finco-route-loader__progress" aria-hidden="true">
        <span />
      </div>
    </div>
  )
}

/**
 * Delayed Suspense fallback for route chunks.
 *
 * Fast chunk loads never flash a second fallback. A separate navigation
 * transition handles the intentional app-like page hand-off, while this
 * fallback takes over if the lazy route itself genuinely needs longer.
 */
export function FinCoRouteLoader() {
  const location = useLocation()
  const [visible, setVisible] = useState(false)
  const destination = useMemo(() => routeDestinationLabel(location.pathname), [location.pathname])

  useEffect(() => {
    const timer = window.setTimeout(() => setVisible(true), 130)
    return () => window.clearTimeout(timer)
  }, [])

  if (!visible) return null
  return <FinCoLoaderVisual destination={destination} />
}
