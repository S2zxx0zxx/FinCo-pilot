import { createContext, useContext } from 'react'

export type InstallOutcome = 'accepted' | 'dismissed' | 'unavailable'

export type PWAContextValue = {
  isOnline: boolean
  isStandalone: boolean
  canInstall: boolean
  updateReady: boolean
  install: () => Promise<InstallOutcome>
  applyUpdate: () => void
}

export const PWAContext = createContext<PWAContextValue | null>(null)

export function usePWA() {
  const context = useContext(PWAContext)
  if (!context) throw new Error('usePWA must be used inside PWAProvider')
  return context
}
