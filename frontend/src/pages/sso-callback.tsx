/**
 * SSO Callback Page
 *
 * Uses Clerk's official AuthenticateWithRedirectCallback to cleanly complete
 * OAuth redirects (e.g. Google), set the session, and transition to the root app (/).
 * On the root app, ProtectedRoute seamlessly exchanges the Clerk session JWT for
 * the FinCo-Pilot access token and opens the dashboard.
 */
import { AuthenticateWithRedirectCallback } from '@clerk/clerk-react'

export default function SSOCallbackPage() {
  return (
    <div className="flex min-h-screen items-center justify-center">
      <AuthenticateWithRedirectCallback
        signInFallbackRedirectUrl="/"
        signUpFallbackRedirectUrl="/"
        continueSignUpUrl="/"
      />
      <div className="flex flex-col items-center gap-4">
        <div className="h-8 w-8 animate-spin rounded-full border-b-2 border-primary" />
        <p className="text-sm text-muted-foreground">Signing you in…</p>
      </div>
    </div>
  )
}
