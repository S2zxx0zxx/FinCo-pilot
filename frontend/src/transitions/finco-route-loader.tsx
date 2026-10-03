import { useMemo } from 'react'
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
      className={`finco-loading-screen${leaving ? ' finco-loading-screen--leaving' : ''}`}
      role="status"
      aria-live="polite"
      aria-label={`Opening ${destination}`}
    >
      <div className="finco-loading-screen__content">
        <div className="finco-loading-screen__mark" aria-hidden="true">
          <span className="finco-loading-screen__halo" />
          <FinCoLogo size={46} className="finco-loading-screen__logo" />
        </div>

        <div className="finco-loading-screen__copy">
          <span className="finco-loading-screen__brand">FinCo-Pilot</span>
          <span className="finco-loading-screen__destination">Opening {destination}</span>
        </div>

        <div className="finco-loading-screen__signal" aria-hidden="true">
          <span />
          <span />
          <span />
        </div>
      </div>
    </div>
  )
}

export function FinCoNavigationPulse({ leaving = false }: { leaving?: boolean }) {
  return (
    <div
      className={`finco-navigation-pulse${leaving ? ' finco-navigation-pulse--leaving' : ''}`}
      aria-hidden="true"
    >
      <span className="finco-navigation-pulse__track">
        <span className="finco-navigation-pulse__bar" />
      </span>
    </div>
  )
}

/**
 * Suspense fallback for real route waits.
 *
 * React Router v7 already wraps router state updates in React transitions, so
 * already-visible content is kept on screen during normal navigations. This
 * fallback is therefore reserved for genuine cold/slow boundaries instead of
 * being artificially delayed or shown on every route change.
 */
export function FinCoRouteLoader() {
  const location = useLocation()
  const destination = useMemo(() => routeDestinationLabel(location.pathname), [location.pathname])

  return <FinCoLoaderVisual destination={destination} />
}
