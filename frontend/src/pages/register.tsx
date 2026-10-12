import {
  useState,
  useEffect,
  type FormEvent,
  type ChangeEvent,
} from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { useTheme } from 'next-themes'
import type { AxiosError } from 'axios'

import { AuthShell } from '@/components/spaceui/auth-shell'
import { TermsLink } from '@/components/terms-link'
import { PrivacyLink } from '@/components/privacy-link'
import { useLaunchText } from '@/lib/launch-copy'
import { useAuth } from '@/contexts/auth-context'
import { admin as adminApi, auth as authApi } from '@/lib/api'
import { resolveSupportedLang } from '@/lib/i18n'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Card, CardContent, CardFooter } from '@/components/ui/card'
import { CurrencySelect } from '@/components/currency-select'
import { FinCoLogo } from '@/components/finco-logo'
import { setThemeBasedOnSystem } from '@/lib/theme-utils'
import { isServerUnreachable } from '@/lib/auth-errors'
import { isClerkConfigured } from '@/lib/clerk-config'
import { useClerkCustomAuth } from '@/lib/clerk-auth-adapter'

interface RegisterFormViewProps {
  readonly email: string
  readonly setEmail: (val: string) => void
  readonly password: string
  readonly setPassword: (val: string) => void
  readonly confirmPassword: string
  readonly setConfirmPassword: (val: string) => void
  readonly currency: string
  readonly setCurrency: (val: string) => void
  readonly error: string
  readonly isLoading: boolean
  readonly onSubmit: (e: FormEvent) => void
  readonly pendingVerification?: boolean
  readonly verificationCode?: string
  readonly setVerificationCode?: (val: string) => void
  readonly onVerifyCode?: (e: FormEvent) => void
  readonly onResendCode?: () => void
  readonly onBackToRegister?: () => void
  readonly isResending?: boolean
  readonly handleGoogleSignUp?: () => void
  readonly isGoogleLoading?: boolean
}

function RegisterFormView({
  email,
  setEmail,
  password,
  setPassword,
  confirmPassword,
  setConfirmPassword,
  currency,
  setCurrency,
  error,
  isLoading,
  onSubmit,
  pendingVerification = false,
  verificationCode = '',
  setVerificationCode,
  onVerifyCode,
  onResendCode,
  onBackToRegister,
  isResending = false,
  handleGoogleSignUp,
  isGoogleLoading = false,
}: RegisterFormViewProps) {
  const tr = useLaunchText()
  const { t } = useTranslation()

  if (pendingVerification) {
    return (
      <AuthShell>
        <Card className="w-full max-w-100 shadow-sm">
          <form onSubmit={onVerifyCode}>
            <div className="flex flex-col items-center pt-8 pb-2 px-8">
              <div className="w-11 h-11 rounded-xl bg-primary/10 flex items-center justify-center mb-4">
                <FinCoLogo size={22} className="text-primary" />
              </div>
              <h1 className="text-xl font-semibold tracking-tight">Verify your email</h1>
              <p className="text-sm text-muted-foreground mt-1 text-center">
                We sent a verification code to <span className="font-medium text-foreground">{email}</span>
              </p>
            </div>
            <CardContent className="space-y-4 px-8 pt-4">
              {error && (
                <div className="p-3 text-sm text-destructive bg-destructive/10 rounded-lg">
                  {error}
                </div>
              )}
              <div className="space-y-1.5">
                <Label htmlFor="verificationCode" className="text-sm">Verification code</Label>
                <Input
                  id="verificationCode"
                  type="text"
                  inputMode="numeric"
                  autoComplete="one-time-code"
                  value={verificationCode}
                  onChange={(e: ChangeEvent<HTMLInputElement>) =>
                    setVerificationCode?.(e.target.value.replace(/[^0-9a-zA-Z]/g, '').slice(0, 10))
                  }
                  placeholder="123456"
                  className="text-center text-lg tracking-[0.3em] font-mono"
                  maxLength={10}
                  required
                  autoFocus
                />
              </div>
            </CardContent>
            <CardFooter className="flex flex-col gap-4 px-8 pb-8 pt-2">
              <Button type="submit" className="w-full" disabled={isLoading || verificationCode.length < 4}>
                {isLoading ? t('common.loading') : 'Verify and complete setup'}
              </Button>
              <div className="flex items-center justify-between w-full text-sm">
                <button
                  type="button"
                  onClick={onResendCode}
                  disabled={isResending}
                  className="text-primary hover:underline text-xs"
                >
                  {isResending ? 'Sending...' : 'Resend code'}
                </button>
                <button
                  type="button"
                  onClick={onBackToRegister}
                  className="text-muted-foreground hover:text-foreground text-xs"
                >
                  Change email
                </button>
              </div>
              <PrivacyLink />
              <TermsLink />
            </CardFooter>
          </form>
        </Card>
      </AuthShell>
    )
  }

  return (
    <AuthShell>
      <Card className="w-full max-w-100 shadow-sm">
        <form onSubmit={onSubmit}>
          <div className="flex flex-col items-center pt-8 pb-2 px-8">
            <div className="w-11 h-11 rounded-xl bg-primary/10 flex items-center justify-center mb-4">
              <FinCoLogo size={22} className="text-primary" />
            </div>
            <h1 className="text-xl font-semibold tracking-tight">{t('auth.register')}</h1>
            <p className="text-sm text-muted-foreground mt-1">{t('auth.registerDescription')}</p>
            <p className="text-sm text-muted-foreground">
              {tr("After signup, check your email for verification. You can request another link from the sign-in page.")}
            </p>
          </div>
          <CardContent className="space-y-4 px-8 pt-4">
            {error && (
              <div className="p-3 text-sm text-destructive bg-destructive/10 rounded-lg">
                {error}
              </div>
            )}
            <div className="space-y-1.5">
              <Label htmlFor="email" className="text-sm">{t('auth.email')}</Label>
              <Input
                id="email"
                type="email"
                value={email}
                onChange={(e: ChangeEvent<HTMLInputElement>) => setEmail(e.target.value)}
                placeholder="you@example.com"
                required
              />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="password" className="text-sm">{t('auth.password')}</Label>
              <Input
                id="password"
                type="password"
                value={password}
                onChange={(e: ChangeEvent<HTMLInputElement>) => setPassword(e.target.value)}
                required
                minLength={8}
              />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="confirmPassword" className="text-sm">{t('auth.confirmPassword')}</Label>
              <Input
                id="confirmPassword"
                type="password"
                value={confirmPassword}
                onChange={(e: ChangeEvent<HTMLInputElement>) => setConfirmPassword(e.target.value)}
                required
              />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="currency" className="text-sm">{t('auth.currency')}</Label>
              <CurrencySelect id="currency" value={currency} onChange={setCurrency} />
            </div>
          </CardContent>
          <CardFooter className="flex flex-col gap-4 px-8 pb-8 pt-2">
            <Button type="submit" className="w-full" disabled={isLoading}>
              {isLoading ? t('common.loading') : t('auth.register')}
            </Button>
            {handleGoogleSignUp && (
              <Button
                id="google-sign-up-btn"
                type="button"
                variant="outline"
                className="w-full flex items-center justify-center gap-2"
                onClick={handleGoogleSignUp}
                disabled={isLoading || isGoogleLoading}
              >
                {isGoogleLoading ? (
                  t('common.loading')
                ) : (
                  <>
                    <svg width="18" height="18" viewBox="0 0 48 48" aria-hidden="true">
                      <path fill="#EA4335" d="M24 9.5c3.54 0 6.71 1.22 9.21 3.6l6.85-6.85C35.9 2.38 30.47 0 24 0 14.62 0 6.51 5.38 2.56 13.22l7.98 6.19C12.43 13.72 17.74 9.5 24 9.5z"/>
                      <path fill="#4285F4" d="M46.98 24.55c0-1.57-.15-3.09-.38-4.55H24v9.02h12.94c-.58 2.96-2.26 5.48-4.78 7.18l7.73 6c4.51-4.18 7.09-10.36 7.09-17.65z"/>
                      <path fill="#FBBC05" d="M10.53 28.59c-.48-1.45-.76-2.99-.76-4.59s.27-3.14.76-4.59l-7.98-6.19C.92 16.46 0 20.12 0 24c0 3.88.92 7.54 2.56 10.78l7.97-6.19z"/>
                      <path fill="#34A853" d="M24 48c6.48 0 11.93-2.13 15.89-5.81l-7.73-6c-2.15 1.45-4.92 2.3-8.16 2.3-6.26 0-11.57-4.22-13.47-9.91l-7.98 6.19C6.51 42.62 14.62 48 24 48z"/>
                      <path fill="none" d="M0 0h48v48H0z"/>
                    </svg>
                    Sign up with Google
                  </>
                )}
              </Button>
            )}
            <p className="text-sm text-muted-foreground">
              {t('auth.hasAccount')}{' '}
              <Link to="/login" className="text-primary font-medium hover:underline">
                {t('auth.login')}
              </Link>
            </p>
            <Link to="/support?from=%2Fregister&category=account_access" className="text-sm text-muted-foreground hover:text-primary hover:underline">
              {t('support.helpLink')}
            </Link>
            <PrivacyLink />
            <TermsLink />
          </CardFooter>
        </form>
      </Card>
    </AuthShell>
  )
}

function ClerkRegisterContainer() {
  const { t, i18n } = useTranslation()
  const { loginWithClerk } = useAuth()
  const clerkAuth = useClerkCustomAuth()
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
    if (clerkAuth.session) {
      void clerkAuth.acquireSessionToken().then(async (tok: string) => {
        if (tok) {
          const lang = resolveSupportedLang(i18n.resolvedLanguage ?? i18n.language)
          await loginWithClerk(tok, undefined, {
            currency_display: currency,
            language: lang,
          })
          navigate('/', { replace: true })
        }
      }).catch(() => {})
    }
  }, [clerkAuth, loginWithClerk, navigate, i18n, currency])

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
      if (result.status === 'needs_verification') {
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

function LocalRegisterContainer() {
  const { t, i18n } = useTranslation()
  const { register } = useAuth()
  const navigate = useNavigate()
  const { resolvedTheme } = useTheme()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [currency, setCurrency] = useState('INR')
  const [error, setError] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [checking, setChecking] = useState(true)

  useEffect(() => {
    let active = true
    Promise.all([
      adminApi.registrationStatus(),
      authApi.oidcConfig().catch(() => null),
    ]).then(([registration, authConfig]) => {
      if (!active) return
      if (!registration.enabled || authConfig?.local_auth_enabled === false) {
        navigate('/login', { replace: true })
        return
      }
      setChecking(false)
    }).catch(() => {
      if (active) setChecking(false)
    })
    adminApi.defaultColors().then(({ light, dark }) => {
      setThemeBasedOnSystem(light, dark, resolvedTheme)
    }).catch(() => {})
    return () => {
      active = false
    }
  }, [navigate, resolvedTheme])

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
      const lang = resolveSupportedLang(i18n.resolvedLanguage ?? i18n.language)
      await register(email, password, {
        currency_display: currency,
        language: lang,
      })
      navigate('/')
    } catch (err) {
      const axiosErr = err as AxiosError
      if (isServerUnreachable(err)) {
        setError(t('auth.serverError'))
      } else if (axiosErr?.response?.status === 429) {
        setError(t('auth.tooManyAttempts'))
      } else {
        setError(t('auth.registrationError'))
      }
    } finally {
      setIsLoading(false)
    }
  }

  if (checking) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" />
      </div>
    )
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
    />
  )
}

export default function RegisterPage() {
  if (isClerkConfigured) {
    return <ClerkRegisterContainer />
  }
  return <LocalRegisterContainer />
}
