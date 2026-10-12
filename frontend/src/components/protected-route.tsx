import { useEffect, useState } from 'react'
import { Navigate } from 'react-router-dom'
import { useAuth } from '@/contexts/auth-context'
import { useAuth as useClerkAuth } from '@clerk/clerk-react'
import { isClerkConfigured } from '@/lib/clerk-config'

function ClerkProtectedRoute({ children }: { children: React.ReactNode }) {
  const { token, isLoading, loginWithClerk } = useAuth()
  const { isLoaded, isSignedIn, getToken } = useClerkAuth()
  const [isExchanging, setIsExchanging] = useState(false)
  const [exchangeError, setExchangeError] = useState<string | null>(null)

  useEffect(() => {
    if (!token && isLoaded && isSignedIn && !isExchanging && !exchangeError) {
      setIsExchanging(true)
      void getToken().then(async (clerkToken) => {
        if (clerkToken) {
          await loginWithClerk(clerkToken)
        }
      }).catch((err: unknown) => {
        console.error('Failed to exchange Clerk token in ProtectedRoute:', err)
        const axiosErr = err as { response?: { data?: { detail?: string } }; message?: string }
        const msg = axiosErr.response?.data?.detail || axiosErr.message || 'sso_failed'
        setExchangeError(msg)
      }).finally(() => {
        setIsExchanging(false)
      })
    }
  }, [token, isLoaded, isSignedIn, isExchanging, exchangeError, getToken, loginWithClerk])

  if (exchangeError) {
    return <Navigate to={`/login?error=${encodeURIComponent(exchangeError)}`} replace />
  }

  if (isLoading || !isLoaded || isExchanging || (!token && isSignedIn)) {
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

  return <>{children}</>
}

function LocalProtectedRoute({ children }: { children: React.ReactNode }) {
  const { token, isLoading } = useAuth()

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

  return <>{children}</>
}

export function ProtectedRoute({ children }: { children: React.ReactNode }) {
  if (isClerkConfigured) {
    return <ClerkProtectedRoute>{children}</ClerkProtectedRoute>
  }
  return <LocalProtectedRoute>{children}</LocalProtectedRoute>
}
