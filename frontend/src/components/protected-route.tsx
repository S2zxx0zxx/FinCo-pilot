import { lazy, Suspense } from 'react'
import { Navigate } from 'react-router-dom'
import { useAuth } from '@/contexts/auth-context'
import { FinCoRouteLoader } from '@/transitions/finco-route-loader'
import { SessionUnavailableNotice } from './session-unavailable-notice'
const ClerkProtectedRoute = lazy(() => import('./clerk-protected-route'))
import { isClerkConfigured } from '@/lib/clerk-config'


function LocalProtectedRoute({ children }: { children: React.ReactNode }) {
  const { token, isLoading, isSessionUnavailable } = useAuth()

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" />
      </div>
    )
  }

  if (!token) {
    return <Navigate to="/login" replace />
  }

  if (isSessionUnavailable) {
    return <SessionUnavailableNotice />
  }

  return <>{children}</>
}

export function ProtectedRoute({ children }: { children: React.ReactNode }) {
  if (isClerkConfigured) {
    return <Suspense fallback={<FinCoRouteLoader />}><ClerkProtectedRoute>{children}</ClerkProtectedRoute></Suspense>
  }
  return <LocalProtectedRoute>{children}</LocalProtectedRoute>
}
