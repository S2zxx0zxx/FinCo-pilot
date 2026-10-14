import { lazy, Suspense, type ReactNode } from 'react'
import { FinCoRouteLoader } from '@/transitions/finco-route-loader'
const ConfiguredClerkProvider = lazy(() => import('./clerk-provider'))

import { isClerkConfigured } from './clerk-config'

export function ClerkProviderWrapper({ children }: { children: ReactNode }) {
  if (!isClerkConfigured) {
    return <>{children}</>
  }

  return <Suspense fallback={<FinCoRouteLoader />}><ConfiguredClerkProvider>{children}</ConfiguredClerkProvider></Suspense>
}
