import { useSignIn, useSignUp, useClerk, useAuth } from '@clerk/clerk-react'
import { useCallback } from 'react'

export interface ClerkAuthResult {
  status: 'complete' | 'needs_verification' | 'needs_requirements' | 'needs_second_factor' | 'other'
  token?: string
  error?: string
}

export function useClerkCustomAuth() {
  const { signIn, setActive: setSignInActive, isLoaded: isSignInLoaded } = useSignIn()
  const { signUp, setActive: setSignUpActive, isLoaded: isSignUpLoaded } = useSignUp()
  const { session } = useClerk()
  const { getToken } = useAuth()

  const acquireSessionToken = useCallback(async (): Promise<string> => {
    try {
      const token = await getToken()
      if (token) return token
    } catch {
      // fallback to session object
    }
    if (session) {
      try {
        const token = await session.getToken()
        if (token) return token
      } catch {
        // failed session getToken
      }
    }
    throw new Error('No active Clerk session token. Please sign in again.')
  }, [getToken, session])

  const signInWithPassword = useCallback(async (
    email: string,
    password: string,
  ): Promise<ClerkAuthResult> => {
    if (!isSignInLoaded || !signIn) {
      throw new Error('Clerk is not yet loaded')
    }

    const attempt = await signIn.create({
      identifier: email.trim(),
      password,
    })

    if (attempt.status === 'complete') {
      await setSignInActive({ session: attempt.createdSessionId })
      const token = await acquireSessionToken()
      return { status: 'complete', token }
    }

    if (attempt.status === 'needs_second_factor') {
      return { status: 'needs_second_factor' }
    }

    return { status: 'other' }
  }, [isSignInLoaded, signIn, setSignInActive, acquireSessionToken])

  /**
   * Initiates Google OAuth sign-in via Clerk's redirect flow.
   * The browser is redirected to Google, then back to /sso-callback
   * where the session token is picked up and exchanged with our backend.
   */
  const signInWithGoogle = useCallback(async (): Promise<void> => {
    if (!isSignInLoaded || !signIn) {
      throw new Error('Clerk is not yet loaded')
    }
    await signIn.authenticateWithRedirect({
      strategy: 'oauth_google',
      redirectUrl: `${window.location.origin}/sso-callback`,
      redirectUrlComplete: `${window.location.origin}/`,
    })
  }, [isSignInLoaded, signIn])

  /**
   * Initiates Google OAuth sign-up via Clerk's redirect flow.
   * New users who haven't registered yet should use this path.
   */
  const signUpWithGoogle = useCallback(async (): Promise<void> => {
    if (!isSignUpLoaded || !signUp) {
      throw new Error('Clerk is not yet loaded')
    }
    await signUp.authenticateWithRedirect({
      strategy: 'oauth_google',
      redirectUrl: `${window.location.origin}/sso-callback`,
      redirectUrlComplete: `${window.location.origin}/`,
    })
  }, [isSignUpLoaded, signUp])

  const verifySecondFactor = useCallback(async (
    code: string,
    strategy: 'totp' | 'phone_code' = 'totp',
  ): Promise<ClerkAuthResult> => {
    if (!isSignInLoaded || !signIn) {
      throw new Error('Clerk is not yet loaded')
    }

    const attempt = await signIn.attemptSecondFactor({
      strategy,
      code: code.trim(),
    })

    if (attempt.status === 'complete') {
      await setSignInActive({ session: attempt.createdSessionId })
      const token = await acquireSessionToken()
      return { status: 'complete', token }
    }

    return { status: 'other' }
  }, [isSignInLoaded, signIn, setSignInActive, acquireSessionToken])

  const signUpWithPassword = useCallback(async (
    email: string,
    password: string,
  ): Promise<ClerkAuthResult> => {
    if (!isSignUpLoaded || !signUp) {
      throw new Error('Clerk is not yet loaded')
    }

    const attempt = await signUp.create({
      emailAddress: email.trim(),
      password,
    })

    if (attempt.status === 'complete') {
      await setSignUpActive({ session: attempt.createdSessionId })
      const token = await acquireSessionToken()
      return { status: 'complete', token }
    }

    // Collect required fields before attempting email verification.
    if (attempt.missingFields?.length) return { status: 'needs_requirements' }
    if (attempt.unverifiedFields?.includes('email_address')) {
      await signUp.prepareEmailAddressVerification({ strategy: 'email_code' })
      return { status: 'needs_verification' }
    }

    return { status: 'other' }
  }, [isSignUpLoaded, signUp, setSignUpActive, acquireSessionToken])

  const verifyEmailCode = useCallback(async (
    code: string,
  ): Promise<ClerkAuthResult> => {
    if (!isSignUpLoaded || !signUp) {
      throw new Error('Clerk is not yet loaded')
    }

    const complete = await signUp.attemptEmailAddressVerification({
      code: code.trim(),
    })

    if (complete.status === 'complete') {
      await setSignUpActive({ session: complete.createdSessionId })
      const token = await acquireSessionToken()
      return { status: 'complete', token }
    }

    if (complete.missingFields?.length) return { status: 'needs_requirements' }
    return { status: 'other' }
  }, [isSignUpLoaded, signUp, setSignUpActive, acquireSessionToken])

  const resendVerificationCode = useCallback(async (): Promise<void> => {
    if (!isSignUpLoaded || !signUp) {
      throw new Error('Clerk is not yet loaded')
    }
    await signUp.prepareEmailAddressVerification({ strategy: 'email_code' })
  }, [isSignUpLoaded, signUp])

  return {
    isLoaded: isSignInLoaded && isSignUpLoaded,
    session,
    acquireSessionToken,
    signInWithPassword,
    signInWithGoogle,
    signUpWithGoogle,
    verifySecondFactor,
    signUpWithPassword,
    verifyEmailCode,
    resendVerificationCode,
  }
}
