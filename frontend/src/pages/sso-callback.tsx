import { useEffect, useRef, useState } from 'react'
import { useClerk } from '@clerk/clerk-react'
import { Link } from 'react-router-dom'

/** The OAuth transfer is consumable: never replay it during StrictMode effects. */
export default function SSOCallbackPage() {
  const clerk = useClerk()
  const loaded = clerk.loaded
  const started = useRef(false)
  const [failed, setFailed] = useState(false)

  useEffect(() => {
    if (!loaded || started.current) return
    started.current = true
    void clerk.handleRedirectCallback({
      signInUrl: '/login',
      signUpUrl: '/sign-up',
      signInFallbackRedirectUrl: '/',
      signUpFallbackRedirectUrl: '/',
      // Google verifies email, but cannot supply an app-specific username.
      continueSignUpUrl: '/sign-up#/continue',
    }).catch(() => {
      // Do not log Clerk resources, OAuth parameters or tokens.
      setFailed(true)
    })
  }, [clerk, loaded])

  return (
    <main className="flex min-h-screen flex-col items-center justify-center gap-4 p-6 text-center">
      {failed ? (
        <>
          <div role="alert">
            <h1 className="text-xl font-semibold">Unable to complete sign-in</h1>
            <p className="mt-2 text-sm text-muted-foreground">
              This sign-in attempt could not be completed. Start a new sign-in attempt to continue.
            </p>
          </div>
          <Link className="underline" to="/login">Return to sign in</Link>
        </>
      ) : (
        <div role="status" className="flex flex-col items-center gap-4">
          <div aria-hidden="true" className="h-8 w-8 animate-spin rounded-full border-b-2 border-primary" />
          <p className="text-sm text-muted-foreground">Completing your sign-in…</p>
        </div>
      )}
    </main>
  )
}
