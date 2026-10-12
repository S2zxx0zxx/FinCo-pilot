/**
 * SSO Callback Page
 *
 * Handles Clerk OAuth redirects (e.g. Google sign-in and sign-up).
 * 1. Completes the OAuth redirect handshake with Clerk.
 * 2. If the user was signing up, activates the created session.
 * 3. Acquires the Clerk session JWT.
 * 4. Exchanges it with the FinCo-Pilot backend (/api/auth/clerk/exchange).
 * 5. Navigates to the dashboard (/).
 */
import { useEffect, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { useClerk, useAuth, useSignUp, useSignIn } from '@clerk/clerk-react'
import { useAuth as useAppAuth } from '@/contexts/auth-context'

export default function SSOCallbackPage() {
  const { handleRedirectCallback, session } = useClerk()
  const { getToken } = useAuth()
  const { signUp, setActive: setSignUpActive } = useSignUp()
  const { signIn, setActive: setSignInActive } = useSignIn()
  const { loginWithClerk } = useAppAuth()
  const navigate = useNavigate()
  const processed = useRef(false)

  useEffect(() => {
    if (processed.current) return
    processed.current = true

    const run = async () => {
      try {
        // Step 1: Let Clerk complete the OAuth handshake
        try {
          await handleRedirectCallback({
            afterSignInUrl: '/sso-callback',
            afterSignUpUrl: '/sso-callback',
            continueSignUpUrl: '/sso-callback',
          })
        } catch (callbackErr) {
          console.warn('handleRedirectCallback notice (proceeding):', callbackErr)
        }

        // Step 2: If sign-up completed, set the session active
        if (signUp?.status === 'complete' && signUp?.createdSessionId && setSignUpActive) {
          try {
            await setSignUpActive({ session: signUp.createdSessionId })
          } catch (e) {
            console.warn('setSignUpActive notice:', e)
          }
        }

        // Step 3: If sign-in completed, set the session active
        if (signIn?.status === 'complete' && signIn?.createdSessionId && setSignInActive) {
          try {
            await setSignInActive({ session: signIn.createdSessionId })
          } catch (e) {
            console.warn('setSignInActive notice:', e)
          }
        }

        // Step 4: Acquire Clerk session JWT token (with retry if session is mounting)
        let attempts = 0
        const acquireAndExchange = async () => {
          let clerkToken: string | null = null
          try {
            clerkToken = await getToken()
          } catch {
            // ignore
          }

          if (!clerkToken && session) {
            try {
              clerkToken = await session.getToken()
            } catch {
              // ignore
            }
          }

          if (clerkToken) {
            await loginWithClerk(clerkToken)
            navigate('/', { replace: true })
            return
          }

          attempts++
          if (attempts < 6) {
            setTimeout(acquireAndExchange, 350)
          } else {
            console.error('No Clerk session token after OAuth callback attempts')
            navigate('/login?error=sso_failed', { replace: true })
          }
        }

        await acquireAndExchange()
      } catch (err) {
        console.error('SSO callback failed:', err)
        navigate('/login?error=sso_failed', { replace: true })
      }
    }

    void run()
  }, [
    handleRedirectCallback,
    session,
    getToken,
    signUp,
    setSignUpActive,
    signIn,
    setSignInActive,
    loginWithClerk,
    navigate,
  ])

  return (
    <div className="flex min-h-screen items-center justify-center">
      <div className="flex flex-col items-center gap-4">
        <div className="h-8 w-8 animate-spin rounded-full border-b-2 border-primary" />
        <p className="text-sm text-muted-foreground">Signing you in…</p>
      </div>
    </div>
  )
}
