import { useSignIn, useSignUp, useClerk, useAuth } from '@clerk/clerk-react'
import { useCallback } from 'react'

export interface ClerkAuthResult {
  status: 'complete' | 'needs_verification' | 'needs_second_factor' | 'other'
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
    return ''
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

    // Default Clerk instances require email verification
    if (
      attempt.status === 'missing_requirements' ||
      attempt.unverifiedFields?.includes('email_address')
    ) {
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
    signInWithPassword,
    verifySecondFactor,
    signUpWithPassword,
    verifyEmailCode,
    resendVerificationCode,
  }
}
