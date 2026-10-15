import { SignUp } from '@clerk/clerk-react'
import { Navigate } from 'react-router-dom'
import { isClerkConfigured } from '@/lib/clerk-config'

/** Clerk validates every configured signup requirement, including username. */
export default function ClerkSignUpPage() {
  if (!isClerkConfigured) return <Navigate to="/register" replace />

  return (
    <main className="flex min-h-screen flex-col items-center justify-center gap-6 p-6">
      <h1 className="text-xl font-semibold">Complete your account</h1>
      <SignUp routing="hash" signInUrl="/login" fallbackRedirectUrl="/dashboard" />
    </main>
  )
}
