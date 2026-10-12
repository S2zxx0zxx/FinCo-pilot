/**
 * SSO Callback Page
 *
 * Clerk redirects back to this page after an OAuth provider (e.g. Google)
 * completes. We then:
 *   1. Wait for Clerk to finish the OAuth handshake and set an active session.
 *   2. Acquire the short-lived Clerk session JWT.
 *   3. Exchange it with the FinCo-Pilot backend (/api/auth/clerk/exchange).
 *   4. Redirect to the dashboard on success, or /login on failure.
 *
 * This page must be registered as an allowed redirect URL in Clerk Dashboard:
 *   https://dashboard.clerk.com → your app → Redirect URLs → add
 *   https://fincopilot.app/sso-callback
 */
import { useEffect, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { useClerk, useAuth } from '@clerk/clerk-react'
import { useAuth as useAppAuth } from '@/contexts/auth-context'

export default function SSOCallbackPage() {
  const { handleRedirectCallback } = useClerk()
  const { getToken } = useAuth()
  const { loginWithClerk } = useAppAuth()
  const navigate = useNavigate()
  const processed = useRef(false)

  useEffect(() => {
    if (processed.current) return
    processed.current = true

    const run = async () => {
      try {
        // Let Clerk complete the OAuth handshake (sets the active session)
        await handleRedirectCallback({
          afterSignInUrl: '/',
          afterSignUpUrl: '/',
        })

        // Acquire the session token from the freshly-created Clerk session
        const clerkToken = await getToken()
        if (!clerkToken) {
          throw new Error('No Clerk session token after OAuth callback')
        }

        // Exchange the Clerk JWT for a FinCo-Pilot access token
        await loginWithClerk(clerkToken)
        navigate('/', { replace: true })
      } catch (err) {
        console.error('SSO callback failed:', err)
        navigate('/login?error=sso_failed', { replace: true })
      }
    }

    void run()
  }, [handleRedirectCallback, getToken, loginWithClerk, navigate])

  return (
    <div className="flex min-h-screen items-center justify-center">
      <div className="flex flex-col items-center gap-4">
        <div className="h-8 w-8 animate-spin rounded-full border-b-2 border-primary" />
        <p className="text-sm text-muted-foreground">Signing you in…</p>
      </div>
    </div>
  )
}
