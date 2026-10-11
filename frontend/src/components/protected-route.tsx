import { Navigate } from 'react-router-dom'
import { useAuth } from '@/contexts/auth-context'
import { loginPaused } from '@/lib/local-ui-preview'

export function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { token, isLoading } = useAuth()

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" />
      </div>
    )
  }

  if (!token) {
    return <Navigate to={loginPaused ? "/" : "/login"} replace />
  }

  return <>{children}</>
}
