import { useEffect, useRef, useState } from 'react'
import { Navigate } from 'react-router-dom'
import { useAuth } from '@/contexts/auth-context'
import { useAuth as useClerkAuth } from '@clerk/clerk-react'
import { isClerkConfigured } from '@/lib/clerk-config'

function SessionUnavailableNotice() {
  return (
    <main role="alert" className="flex min-h-screen flex-col items-center justify-center gap-4 p-6 text-center">
      <h1 className="text-xl font-semibold">Unable to verify your session</h1>
      <p className="max-w-md text-sm text-muted-foreground">
        FinCo-Pilot is temporarily unavailable. Your sign-in has not been discarded.
        No account data will be shown until the server can verify your session.
      </p>
      <button
        type="button"
        className="rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground"
        onClick={() => window.location.reload()}
      >
        Retry connection
      </button>
    </main>
  )
}

function ClerkProtectedRoute({ children }: { children: React.ReactNode }) {
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
    return <ClerkProtectedRoute>{children}</ClerkProtectedRoute>
  }
  return <LocalProtectedRoute>{children}</LocalProtectedRoute>
}
