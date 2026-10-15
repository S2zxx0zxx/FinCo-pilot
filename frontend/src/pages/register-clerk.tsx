import { useState, useEffect, useRef, type FormEvent } from 'react'
import { useTranslation } from 'react-i18next'
import { useTheme } from 'next-themes'
import { useAuth } from '@/contexts/auth-context'
import { admin as adminApi } from '@/lib/api'
import { setThemeBasedOnSystem } from '@/lib/theme-utils'
import { useClerkCustomAuth } from '@/lib/clerk-auth-adapter'
import { useNavigate } from 'react-router-dom'
import { resolveSupportedLang } from '@/lib/i18n'
import { RegisterFormView } from './register'

// Existing provider flow; only the module loading boundary changed.
export default function ClerkRegisterContainer() {
  const { t, i18n } = useTranslation()
  const { token, loginWithClerk } = useAuth()
  const clerkAuth = useClerkCustomAuth()
  const { session: clerkSession, acquireSessionToken } = clerkAuth
  const exchangeAttempt = useRef<string | null>(null)
  const navigate = useNavigate()
  const { resolvedTheme } = useTheme()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [currency, setCurrency] = useState('INR')
  const [error, setError] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [isGoogleLoading, setIsGoogleLoading] = useState(false)
  const [pendingVerification, setPendingVerification] = useState(false)
  const [verificationCode, setVerificationCode] = useState('')
  const [isResending, setIsResending] = useState(false)

  useEffect(() => {
    void adminApi.defaultColors().then(({ light, dark }) => {
      setThemeBasedOnSystem(light, dark, resolvedTheme)
    }).catch(() => {})
  }, [resolvedTheme])

  useEffect(() => {
    if (!token && clerkSession && exchangeAttempt.current !== clerkSession.id) {
      exchangeAttempt.current = clerkSession.id
      void acquireSessionToken().then(async (tok: string) => {
        if (tok) {
          const lang = resolveSupportedLang(i18n.resolvedLanguage ?? i18n.language)
          await loginWithClerk(tok, undefined, {
            currency_display: currency,
            language: lang,
          })
          navigate('/', { replace: true })
        }
      }).catch(() => { setError(t('auth.registrationError')) })
    }
  }, [token, clerkSession, acquireSessionToken, loginWithClerk, navigate, i18n, currency, t])

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault()
    setError('')

    if (password !== confirmPassword) {
      setError(t('auth.passwordMismatch'))
      return
    }

    if (password.length < 8) {
      setError(t('auth.passwordTooShort'))
      return
    }

    setIsLoading(true)
    try {
      const result = await clerkAuth.signUpWithPassword(email, password)
      if (result.status === 'needs_requirements') {
        navigate('/sign-up#/continue')
      } else if (result.status === 'needs_verification') {
        setPendingVerification(true)
      } else if (result.status === 'complete' && result.token) {
        const lang = resolveSupportedLang(i18n.resolvedLanguage ?? i18n.language)
        await loginWithClerk(result.token, email, {
          currency_display: currency,
          language: lang,
        })
        navigate('/')
      }
    } catch (err: unknown) {
      const clerkErr = err as { errors?: Array<{ message?: string; longMessage?: string; code?: string }> }
      if (clerkErr?.errors?.length) {
        setError(clerkErr.errors[0].longMessage || clerkErr.errors[0].message || t('auth.registrationError'))
      } else {
        setError(t('auth.registrationError'))
      }
    } finally {
      setIsLoading(false)
    }
  }

  const handleVerifyCode = async (e: FormEvent) => {
    e.preventDefault()
    setError('')
    setIsLoading(true)
    try {
      const result = await clerkAuth.verifyEmailCode(verificationCode)
      if (result.status === 'complete' && result.token) {
        const lang = resolveSupportedLang(i18n.resolvedLanguage ?? i18n.language)
        await loginWithClerk(result.token, email, {
          currency_display: currency,
          language: lang,
        })
        navigate('/')
      } else if (result.status === 'needs_requirements') {
        navigate('/sign-up#/continue')
      } else {
        setError('Verification code is invalid or expired')
      }
    } catch (err: unknown) {
      const clerkErr = err as { errors?: Array<{ message?: string; longMessage?: string; code?: string }> }
      if (clerkErr?.errors?.length) {
        setError(clerkErr.errors[0].longMessage || clerkErr.errors[0].message || 'Invalid verification code')
      } else {
        setError('Invalid verification code')
      }
    } finally {
      setIsLoading(false)
    }
  }

  const handleResendCode = async () => {
    setIsResending(true)
    try {
      await clerkAuth.resendVerificationCode()
    } catch {
      // Ignored
    } finally {
      setIsResending(false)
    }
  }

  const handleGoogleSignUp = async () => {
    setError('')
    setIsGoogleLoading(true)
    try {
      await clerkAuth.signUpWithGoogle()
      // SSO callback page handles token exchange after redirect
    } catch (err: unknown) {
      const clerkErr = err as { errors?: Array<{ message?: string; longMessage?: string }> }
      if (clerkErr?.errors?.length) {
        setError(clerkErr.errors[0].longMessage || clerkErr.errors[0].message || 'Google sign-up failed')
      } else {
        setError('Google sign-up failed. Please try again.')
      }
      setIsGoogleLoading(false)
    }
  }

  return (
    <RegisterFormView
      email={email}
      setEmail={setEmail}
      password={password}
      setPassword={setPassword}
      confirmPassword={confirmPassword}
      setConfirmPassword={setConfirmPassword}
      currency={currency}
      setCurrency={setCurrency}
      error={error}
      isLoading={isLoading}
      onSubmit={handleSubmit}
      pendingVerification={pendingVerification}
      verificationCode={verificationCode}
      setVerificationCode={setVerificationCode}
      onVerifyCode={handleVerifyCode}
      onResendCode={handleResendCode}
      onBackToRegister={() => setPendingVerification(false)}
      isResending={isResending}
      handleGoogleSignUp={handleGoogleSignUp}
      isGoogleLoading={isGoogleLoading}
    />
  )
}
