import { useEffect, useRef, useState } from 'react'
import { Navigate } from 'react-router-dom'
import { useAuth } from '@/contexts/auth-context'
import { useAuth as useClerkAuth } from '@clerk/clerk-react'
import { SessionUnavailableNotice } from './session-unavailable-notice'

export default function ClerkProtectedRoute({ children }: { children: React.ReactNode }) {
  const { token, isLoading, isSessionUnavailable, loginWithClerk } = useAuth()
  const { isLoaded, isSignedIn, getToken } = useClerkAuth()
  const exchangeInFlight = useRef(false)
  const [exchangeError, setExchangeError] = useState<string | null>(null)

  useEffect(() => {
    if (!token && isLoaded && isSignedIn && !exchangeInFlight.current && !exchangeError) {
      exchangeInFlight.current = true
      void getToken().then(async (clerkToken) => {
        if (!clerkToken) {
          throw new Error('Clerk did not return a session token. Please sign in again.')
        }
        await loginWithClerk(clerkToken)
      }).catch((err: unknown) => {
        const axiosErr = err as { response?: { data?: { detail?: string } }; message?: string }
        const msg = axiosErr.response?.data?.detail || axiosErr.message || 'sso_failed'
        setExchangeError(msg)
      }).finally(() => {
        exchangeInFlight.current = false
      })
    }
  }, [token, isLoaded, isSignedIn, exchangeError, getToken, loginWithClerk])

  if (exchangeError) {
    return <Navigate to={`/login?error=${encodeURIComponent(exchangeError)}`} replace />
  }

  if (isLoading || !isLoaded || (!token && isSignedIn)) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="flex flex-col items-center gap-4">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" />
          <p className="text-sm text-muted-foreground">Signing you in…</p>
        </div>
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
