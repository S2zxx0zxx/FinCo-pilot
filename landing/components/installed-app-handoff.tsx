'use client'

import { useEffect } from 'react'

/** Preserve old PWA installations whose start_url was the public root.
 * This changes navigation only: /dashboard still requires the normal auth gate.
 */
export function InstalledAppHandoff() {
  useEffect(() => {
    if (process.env.NEXT_PUBLIC_FINCO_SAME_ORIGIN !== 'true') return
    const iosStandalone = (navigator as Navigator & { standalone?: boolean }).standalone === true
    if (iosStandalone || window.matchMedia('(display-mode: standalone)').matches) {
      window.location.replace('/dashboard')
    }
  }, [])
  return null
}
