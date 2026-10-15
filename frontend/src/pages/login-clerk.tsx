import { useState, useEffect, useRef, type FormEvent } from 'react'
import { useTranslation } from 'react-i18next'
import { useTheme } from 'next-themes'
import { useAuth } from '@/contexts/auth-context'
import { admin as adminApi } from '@/lib/api'
import { setThemeBasedOnSystem } from '@/lib/theme-utils'
import { useClerkCustomAuth } from '@/lib/clerk-auth-adapter'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { isServerUnreachable } from '@/lib/auth-errors'
import { LoginFormView } from './login'

// Existing provider flow; only the module loading boundary changed.
export default function ClerkLoginContainer() {
  const { t } = useTranslation()
  const { loginWithClerk, token } = useAuth()
  const clerkAuth = useClerkCustomAuth()
  const { session: clerkSession, acquireSessionToken } = clerkAuth
  const exchangeAttemptRef = useRef<string | null>(null)
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const { resolvedTheme } = useTheme()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [isGoogleLoading, setIsGoogleLoading] = useState(false)
  const [registrationEnabled, setRegistrationEnabled] = useState(true)

  // 2FA state
  const [requires2fa, setRequires2fa] = useState(false)
  const [totpCode, setTotpCode] = useState('')

  const requestedNext = searchParams.get('next')
  const safeNext = requestedNext === '/' ? '/dashboard' : requestedNext?.startsWith('/') && !requestedNext.startsWith('//') && !requestedNext.includes('://')
    ? requestedNext
    : '/dashboard'

  useEffect(() => {
    const urlErr = searchParams.get('error')
    if (urlErr) {
      setError(urlErr === 'sso_failed' ? 'Google authentication failed. Please try again.' : urlErr)
    }
  }, [searchParams])

  useEffect(() => {
    if (token) {
      navigate(safeNext, { replace: true })
      return
    }
    if (clerkSession) {
      // A new adapter object is returned per render. Track session ID instead:
      // failed exchanges must not retrigger forever on every error repaint.
      if (exchangeAttemptRef.current !== clerkSession.id) {
        exchangeAttemptRef.current = clerkSession.id
        void acquireSessionToken().then(async (tok: string) => {
          if (!tok) throw new Error('No active Clerk session token. Please sign in again.')
          await loginWithClerk(tok)
          navigate(safeNext, { replace: true })
        }).catch((err: unknown) => {
          const axiosErr = err as { response?: { status?: number; data?: { detail?: string } }; message?: string }
          const msg = axiosErr.response?.status && axiosErr.response.status >= 500
            ? t('auth.serverError')
            : axiosErr.response?.data?.detail || axiosErr.message || 'Clerk login exchange failed'
          setError(msg)
        })
      }
      return
    }
    void adminApi.registrationStatus().then(({ enabled }) => {
      setRegistrationEnabled(enabled)
    }).catch(() => {})
    void adminApi.defaultColors().then(({ light, dark }) => {
      setThemeBasedOnSystem(light, dark, resolvedTheme)
    }).catch(() => {})
  }, [navigate, token, resolvedTheme, clerkSession, acquireSessionToken, loginWithClerk, safeNext, t])

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault()
    setError('')
    setIsLoading(true)
    try {
      const result = await clerkAuth.signInWithPassword(email, password)
      if (result.status === 'complete' && result.token) {
        await loginWithClerk(result.token, email)
        navigate(safeNext)
      } else if (result.status === 'needs_second_factor') {
        setRequires2fa(true)
      } else {
        setError(t('auth.invalidCredentials'))
      }
    } catch (err: unknown) {
      const clerkErr = err as { errors?: Array<{ message?: string; longMessage?: string; code?: string }> }
      if (clerkErr?.errors?.length) {
        setError(clerkErr.errors[0].longMessage || clerkErr.errors[0].message || t('auth.invalidCredentials'))
      } else if (isServerUnreachable(err)) {
        setError(t('auth.serverError'))
      } else {
        const axiosErr = err as { response?: { status?: number; data?: { detail?: string } } }
        setError(axiosErr.response?.status === 403
          ? axiosErr.response.data?.detail || t('auth.invalidCredentials')
          : t('auth.invalidCredentials'))
      }
    } finally {
      setIsLoading(false)
    }
  }

  const handleVerify2fa = async (e: FormEvent) => {
    e.preventDefault()
    setError('')
    setIsLoading(true)
    try {
      const result = await clerkAuth.verifySecondFactor(totpCode)
      if (result.status === 'complete' && result.token) {
        await loginWithClerk(result.token, email)
        navigate(safeNext)
      } else {
        setError(t('auth.invalid2faCode'))
      }
    } catch (err: unknown) {
      const clerkErr = err as { errors?: Array<{ message?: string; longMessage?: string; code?: string }> }
      if (clerkErr?.errors?.length) {
        setError(clerkErr.errors[0].longMessage || clerkErr.errors[0].message || t('auth.invalid2faCode'))
      } else {
        setError(t('auth.invalid2faCode'))
      }
    } finally {
      setIsLoading(false)
    }
  }

  const resetSecondFactor = () => {
    setRequires2fa(false)
    setTotpCode('')
    setError('')
  }

  const handleGoogleSignIn = async () => {
    setError('')
    setIsGoogleLoading(true)
    try {
      await clerkAuth.signInWithGoogle()
      // After redirect returns, the sso-callback page handles the rest
    } catch (err: unknown) {
      const clerkErr = err as { errors?: Array<{ message?: string; longMessage?: string }> }
      if (clerkErr?.errors?.length) {
        setError(clerkErr.errors[0].longMessage || clerkErr.errors[0].message || 'Google sign-in failed')
      } else {
        setError('Google sign-in failed. Please try again.')
      }
      setIsGoogleLoading(false)
    }
  }

  return (
    <LoginFormView
      email={email}
      setEmail={setEmail}
      password={password}
      setPassword={setPassword}
      error={error}
      isLoading={isLoading}
      requires2fa={requires2fa}
      totpCode={totpCode}
      setTotpCode={setTotpCode}
      handleSubmit={handleSubmit}
      handleVerify2fa={handleVerify2fa}
      resetSecondFactor={resetSecondFactor}
      registrationEnabled={registrationEnabled}
      localAuthEnabled={true}
      handleGoogleSignIn={handleGoogleSignIn}
      isGoogleLoading={isGoogleLoading}
    />
  )
}
