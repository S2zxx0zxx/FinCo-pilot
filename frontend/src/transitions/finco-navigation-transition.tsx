import { useEffect, useRef, useState } from 'react'
import { useLocation } from 'react-router-dom'
import { FinCoLoaderVisual, routeDestinationLabel } from '@/transitions/finco-route-loader'

const HOLD_MS = 360
const EXIT_MS = 180

/**
 * Native-feeling hand-off for real page/section navigation.
 *
 * The route starts loading immediately; this overlay never delays the router or
 * network. It simply covers the visual hand-off for a short, consistent window
 * so users do not see layout flashes between large finance sections.
 */
export function FinCoNavigationTransition() {
  const location = useLocation()
  const mounted = useRef(false)
  const sequence = useRef(0)
  const [state, setState] = useState<{
    destination: string
    leaving: boolean
  } | null>(null)

  useEffect(() => {
    if (!mounted.current) {
      mounted.current = true
      return
    }

    const current = ++sequence.current
    const destination = routeDestinationLabel(location.pathname)
    setState({ destination, leaving: false })

    const beginExit = window.setTimeout(() => {
      if (sequence.current === current) {
        setState((value) => value ? { ...value, leaving: true } : null)
      }
    }, HOLD_MS)

    const finish = window.setTimeout(() => {
      if (sequence.current === current) setState(null)
    }, HOLD_MS + EXIT_MS)

    return () => {
      window.clearTimeout(beginExit)
      window.clearTimeout(finish)
    }
  }, [location.pathname])

  if (!state) return null
  return <FinCoLoaderVisual destination={state.destination} leaving={state.leaving} />
}
