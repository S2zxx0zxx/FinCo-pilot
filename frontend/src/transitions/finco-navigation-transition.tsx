import { useEffect, useRef, useState } from 'react'
import { useLocation } from 'react-router-dom'
import { FinCoNavigationPulse } from '@/transitions/finco-route-loader'

const HOLD_MS = 180
const EXIT_MS = 90

/**
 * Non-blocking route feedback.
 *
 * The previous implementation covered the whole app for ~540 ms after every
 * pathname change, which made fast navigation feel artificially slow. This
 * version keeps the destination UI visible and only paints a slim pulse rail
 * at the top edge for a brief hand-off.
 */
export function FinCoNavigationTransition() {
  const location = useLocation()
  const mounted = useRef(false)
  const sequence = useRef(0)
  const [leaving, setLeaving] = useState<boolean | null>(null)

  useEffect(() => {
    if (!mounted.current) {
      mounted.current = true
      return
    }

    const current = ++sequence.current
    const showFrame = window.requestAnimationFrame(() => {
      if (sequence.current === current) setLeaving(false)
    })

    const beginExit = window.setTimeout(() => {
      if (sequence.current === current) setLeaving(true)
    }, HOLD_MS)

    const finish = window.setTimeout(() => {
      if (sequence.current === current) setLeaving(null)
    }, HOLD_MS + EXIT_MS)

    return () => {
      window.cancelAnimationFrame(showFrame)
      window.clearTimeout(beginExit)
      window.clearTimeout(finish)
    }
  }, [location.pathname])

  if (leaving === null) return null
  return <FinCoNavigationPulse leaving={leaving} />
}
