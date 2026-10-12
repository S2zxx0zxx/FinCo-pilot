import {
  useState,
  useEffect,
  useRef,
  type FormEvent,
  type ChangeEvent,
} from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { useTheme } from 'next-themes'
import type { AxiosError } from 'axios'

import { AuthShell } from '@/components/spaceui/auth-shell'
import { TermsLink } from '@/components/terms-link'
import { PrivacyLink } from '@/components/privacy-link'
import { FinCoLogo } from '@/components/finco-logo'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Card, CardContent, CardFooter } from '@/components/ui/card'
import { useAuth } from '@/contexts/auth-context'
import { setup, auth as authApi, admin as adminApi } from '@/lib/api'
import { isServerUnreachable } from '@/lib/auth-errors'
import { resolveLocalAuthEnabled } from '@/lib/auth-config-utils'
import { setThemeBasedOnSystem } from '@/lib/theme-utils'
import { isClerkConfigured } from '@/lib/clerk-config'
import { useClerkCustomAuth } from '@/lib/clerk-auth-adapter'
import {
  isConditionalPasskeySupported,
  isPasskeySupported,
  passkeyFailure,
  startConditionalPasskeyAuthentication,
  startPasskeyAuthentication,
} from '@/lib/webauthn'
import type { PasskeyFailure } from '@/lib/webauthn'

const PASSKEY_LOGIN_FAILURE_KEYS: Record<PasskeyFailure, string> = {
  cancelled: 'auth.passkeyCancelled',
  domain: 'auth.passkeyDomainError',
  mismatch: 'auth.passkeyDomainMismatch',
  ip: 'auth.passkeyIpAddress',
  insecure: 'auth.passkeyInsecureContext',
  unsupported: 'auth.passkeyUnsupported',
  duplicate: 'auth.passkeyLoginError',
  unknown: 'auth.passkeyLoginError',
}

type OIDCConfig = {
  readonly enabled: boolean
  readonly provider_name: string
  readonly local_auth_enabled: boolean
}

interface TwoFactorCardProps {
  readonly error: string
  readonly isLoading: boolean
  readonly totpCode: string
  readonly setTotpCode: (val: string) => void
  readonly handleVerify2fa: (e: FormEvent) => void
  readonly resetSecondFactor: () => void
  readonly selected2faMethod?: 'totp' | 'passkey'
  readonly setSelected2faMethod?: (method: 'totp' | 'passkey') => void
  readonly available2faMethods?: readonly ('totp' | 'passkey')[]
  readonly handlePasskeySecondFactor?: () => void
  readonly isPasskeyLoading?: boolean
  readonly passkeySupported?: boolean
}

function TwoFactorCard({
  error,
  isLoading,
  totpCode,
  setTotpCode,
  handleVerify2fa,
  resetSecondFactor,
  selected2faMethod = 'totp',
  setSelected2faMethod,
  available2faMethods = ['totp'],
  handlePasskeySecondFactor,
  isPasskeyLoading = false,
  passkeySupported = false,
}: TwoFactorCardProps) {
  const { t } = useTranslation()

  return (
    <AuthShell>
      <Card className="finco-auth-card w-full max-w-105">
        <form onSubmit={handleVerify2fa}>
          <div className="flex flex-col items-center pt-8 pb-2 px-8">
            <div className="w-11 h-11 rounded-xl bg-primary/10 flex items-center justify-center mb-4">
              <FinCoLogo size={22} className="text-primary" />
            </div>
            <h1 className="text-xl font-semibold tracking-tight">
              {selected2faMethod === 'passkey' ? t('auth.passkeySecondFactorTitle') : t('auth.twoFactorTitle')}
            </h1>
            <p className="text-sm text-muted-foreground mt-1 text-center">
              {selected2faMethod === 'passkey'
                ? t('auth.passkeySecondFactorDescription')
                : t('auth.twoFactorDescription')}
            </p>
          </div>
          <CardContent className="space-y-4 px-8 pt-4">
            {error && (
              <div className="p-3 text-sm text-destructive bg-destructive/10 rounded-lg">
                {error}
              </div>
            )}
            {available2faMethods.length > 1 && setSelected2faMethod && (
              <div className="grid grid-cols-2 gap-2">
                {available2faMethods.includes('passkey') && (
                  <Button
                    type="button"
                    variant={selected2faMethod === 'passkey' ? 'default' : 'outline'}
                    onClick={() => setSelected2faMethod('passkey')}
                  >
                    {t('auth.passkeyMethod')}
                  </Button>
                )}
                {available2faMethods.includes('totp') && (
                  <Button
                    type="button"
                    variant={selected2faMethod === 'totp' ? 'default' : 'outline'}
                    onClick={() => setSelected2faMethod('totp')}
                  >
                    {t('auth.totpMethod')}
                  </Button>
                )}
              </div>
            )}
            {selected2faMethod === 'totp' && (
              <div className="space-y-1.5">
                <Label htmlFor="totp-code" className="text-sm">Authenticator code or one-time recovery code</Label>
                <Input
                  id="totp-code"
                  type="text"
                  inputMode="text"
                  autoComplete="one-time-code"
                  value={totpCode}
                  onChange={(e: ChangeEvent<HTMLInputElement>) =>
                    setTotpCode(e.target.value.replace(/[^a-fA-F0-9]/g, '').slice(0, 20))
                  }
                  placeholder="Authenticator or recovery code"
                  className="text-center text-lg tracking-[0.3em] font-mono"
                  maxLength={20}
                  required
                  autoFocus
                />
              </div>
            )}
            {selected2faMethod === 'passkey' && (
              <p className="text-sm text-muted-foreground text-center">
                {t('auth.passkeySecondFactorPrompt')}
              </p>
            )}
          </CardContent>
          <CardFooter className="flex flex-col gap-4 px-8 pb-8 pt-2">
            {selected2faMethod === 'totp' ? (
              <Button type="submit" className="w-full" disabled={isLoading || ![6, 20].includes(totpCode.length)}>
                {isLoading ? t('common.loading') : t('auth.verify')}
              </Button>
            ) : (
              <Button
                type="button"
                className="w-full"
                onClick={handlePasskeySecondFactor}
                disabled={isLoading || isPasskeyLoading || !passkeySupported}
              >
                {isPasskeyLoading ? t('common.loading') : t('auth.usePasskeySecondFactor')}
              </Button>
            )}
            <div className="flex items-center gap-4 text-sm">
              <button
                type="button"
                onClick={resetSecondFactor}
                className="text-muted-foreground hover:text-foreground"
              >
                {t('auth.login')}
              </button>
              <Link to="/support?from=%2Flogin&category=account_access" className="text-primary hover:underline">
                {t('support.helpLink')}
              </Link>
            </div>
            <PrivacyLink />
            <TermsLink />
          </CardFooter>
        </form>
      </Card>
    </AuthShell>
  )
}

interface LoginFormViewProps {
  readonly email: string
  readonly setEmail: (val: string) => void
  readonly password: string
  readonly setPassword: (val: string) => void
  readonly error: string
  readonly isLoading: boolean
  readonly requires2fa: boolean
  readonly totpCode: string
  readonly setTotpCode: (val: string) => void
  readonly handleSubmit: (e: FormEvent) => void
  readonly handleVerify2fa: (e: FormEvent) => void
  readonly resetSecondFactor: () => void
  readonly authConfigLoading?: boolean
  readonly oidcConfigFailed?: boolean
  readonly noAuthMethodConfigured?: boolean
  readonly localAuthEnabled?: boolean
  readonly showAuthDivider?: boolean
  readonly showPasskeyLogin?: boolean
  readonly handlePasskeyLogin?: () => void
  readonly isPasskeyLoading?: boolean
  readonly oidcEnabled?: boolean
  readonly handleOIDCLogin?: () => void
  readonly oidcConfig?: OIDCConfig | null
  readonly registrationEnabled?: boolean
  readonly selected2faMethod?: 'totp' | 'passkey'
  readonly setSelected2faMethod?: (method: 'totp' | 'passkey') => void
  readonly available2faMethods?: readonly ('totp' | 'passkey')[]
  readonly handlePasskeySecondFactor?: () => void
  readonly passkeySupported?: boolean
  readonly handleGoogleSignIn?: () => void
  readonly isGoogleLoading?: boolean
}

function LoginFormView(props: LoginFormViewProps) {
  const { t } = useTranslation()

  if (props.requires2fa) {
    return (
      <TwoFactorCard
        error={props.error}
        isLoading={props.isLoading}
        totpCode={props.totpCode}
        setTotpCode={props.setTotpCode}
        handleVerify2fa={props.handleVerify2fa}
        resetSecondFactor={props.resetSecondFactor}
        selected2faMethod={props.selected2faMethod}
        setSelected2faMethod={props.setSelected2faMethod}
        available2faMethods={props.available2faMethods}
        handlePasskeySecondFactor={props.handlePasskeySecondFactor}
        isPasskeyLoading={props.isPasskeyLoading}
        passkeySupported={props.passkeySupported}
      />
    )
  }

  return (
    <AuthShell>
      <Card className="finco-auth-card w-full max-w-105">
        <form onSubmit={props.handleSubmit}>
          <div className="flex flex-col items-center pt-8 pb-2 px-8">
            <div className="w-11 h-11 rounded-xl bg-primary/10 flex items-center justify-center mb-4">
              <FinCoLogo size={22} className="text-primary" />
            </div>
            <h1 className="text-xl font-semibold tracking-tight">{t('auth.login')}</h1>
            <p className="text-sm text-muted-foreground mt-1">{t('auth.loginDescription')}</p>
          </div>
          {props.authConfigLoading && (
            <CardContent className="px-8 py-6 text-center text-sm text-muted-foreground" role="status">
              {t('common.loading')}
            </CardContent>
          )}
          {props.oidcConfigFailed && (
            <CardContent className="px-8 py-4">
              <div role="alert" className="p-3 text-sm text-muted-foreground bg-muted rounded-lg">
                {t('auth.authConfigUnavailable')}
              </div>
            </CardContent>
          )}
          {props.noAuthMethodConfigured && (
            <CardContent className="px-8 py-4">
              <div role="alert" className="p-3 text-sm text-destructive bg-destructive/10 rounded-lg">
                {t('auth.noAuthMethodConfigured')}
              </div>
            </CardContent>
          )}
          {props.localAuthEnabled && (
            <CardContent className="space-y-4 px-8 pt-4">
              {props.error && (
                <div className="p-3 text-sm text-destructive bg-destructive/10 rounded-lg">
                  {props.error}
                </div>
              )}
              <div className="space-y-1.5">
                <Label htmlFor="email" className="text-sm">{t('auth.email')}</Label>
                <Input
                  id="email"
                  type="email"
                  value={props.email}
                  onChange={(e: ChangeEvent<HTMLInputElement>) => props.setEmail(e.target.value)}
                  placeholder="you@example.com"
                  autoComplete="username webauthn"
                  required
                />
              </div>
              <div className="space-y-1.5">
                <div className="flex justify-between">
                  <Label htmlFor="password" className="text-sm">{t('auth.password')}</Label>
                  <span className="flex gap-2 text-xs">
                    <Link to="/request-verification" className="underline">Verify email</Link>
                    <Link to="/forgot-password" className="underline">Forgot password?</Link>
                  </span>
                </div>
                <Input
                  id="password"
                  type="password"
                  value={props.password}
                  onChange={(e: ChangeEvent<HTMLInputElement>) => props.setPassword(e.target.value)}
                  autoComplete="current-password"
                  required
                />
              </div>
            </CardContent>
          )}
          {!props.authConfigLoading && !props.noAuthMethodConfigured && (
            <CardFooter className={`flex flex-col gap-4 px-8 pb-8 ${props.localAuthEnabled ? 'pt-2' : 'pt-6'}`}>
              {props.localAuthEnabled && (
                <Button type="submit" className="w-full" disabled={props.isLoading || props.isPasskeyLoading}>
                  {props.isLoading ? t('common.loading') : t('auth.login')}
                </Button>
              )}
              {(props.showAuthDivider || (props.localAuthEnabled && props.handleGoogleSignIn)) && (
                <div className="flex items-center gap-3 w-full">
                  <div className="h-px flex-1 bg-border" />
                  <span className="text-xs text-muted-foreground">{t('auth.or')}</span>
                  <div className="h-px flex-1 bg-border" />
                </div>
              )}
              {props.showPasskeyLogin && props.handlePasskeyLogin && (
                <Button
                  type="button"
                  variant="outline"
                  className="w-full"
                  onClick={props.handlePasskeyLogin}
                  disabled={props.isLoading || props.isPasskeyLoading}
                >
                  {props.isPasskeyLoading ? t('common.loading') : t('auth.loginWithPasskey')}
                </Button>
              )}
              {props.handleGoogleSignIn && (
                <Button
                  id="google-sign-in-btn"
                  type="button"
                  variant="outline"
                  className="w-full flex items-center justify-center gap-2"
                  onClick={props.handleGoogleSignIn}
                  disabled={props.isLoading || props.isGoogleLoading || props.isPasskeyLoading}
                >
                  {props.isGoogleLoading ? (
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
                      Continue with Google
                    </>
                  )}
                </Button>
              )}
              {props.oidcEnabled && props.handleOIDCLogin && (
                <Button
                  type="button"
                  variant={props.localAuthEnabled ? 'outline' : 'default'}
                  className="w-full"
                  onClick={props.handleOIDCLogin}
                >
                  {t('auth.loginWithProvider', { provider: props.oidcConfig?.provider_name ?? 'OIDC' })}
                </Button>
              )}
              {props.localAuthEnabled && props.registrationEnabled && (
                <p className="text-sm text-muted-foreground">
                  {t('auth.noAccount')}{' '}
                  <Link to="/register" className="text-primary font-medium hover:underline">
                    {t('auth.register')}
                  </Link>
                </p>
              )}
              <Link to="/support?from=%2Flogin&category=account_access" className="text-sm text-muted-foreground hover:text-primary hover:underline">
                {t('support.helpLink')}
              </Link>
              <PrivacyLink />
              <TermsLink />
            </CardFooter>
          )}
        </form>
      </Card>
    </AuthShell>
  )
}

function ClerkLoginContainer() {
  const { t } = useTranslation()
  const { loginWithClerk, token } = useAuth()
  const clerkAuth = useClerkCustomAuth()
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
  const safeNext = requestedNext?.startsWith('/') && !requestedNext.startsWith('//') && !requestedNext.includes('://')
    ? requestedNext
    : '/'

  useEffect(() => {
    if (token) {
      navigate('/', { replace: true })
      return
    }
    adminApi.registrationStatus().then(({ enabled }) => {
      setRegistrationEnabled(enabled)
    }).catch(() => {})
    adminApi.defaultColors().then(({ light, dark }) => {
      setThemeBasedOnSystem(light, dark, resolvedTheme)
    }).catch(() => {})
  }, [navigate, token, resolvedTheme])

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
      } else {
        setError(t('auth.invalidCredentials'))
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

function LocalLoginContainer() {
  const { t } = useTranslation()
  const { login, verify2fa, loginWithToken, token } = useAuth()
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const { resolvedTheme } = useTheme()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [isPasskeyLoading, setIsPasskeyLoading] = useState(false)
  const [passkeySupported, setPasskeySupported] = useState(false)
  const [registrationEnabled, setRegistrationEnabled] = useState(true)
  const [oidcConfig, setOidcConfig] = useState<OIDCConfig | null>(null)
  const [oidcConfigFailed, setOidcConfigFailed] = useState(false)

  // 2FA state
  const [requires2fa, setRequires2fa] = useState(false)
  const [tempToken, setTempToken] = useState('')
  const [totpCode, setTotpCode] = useState('')
  const [available2faMethods, setAvailable2faMethods] = useState<Array<'totp' | 'passkey'>>(['totp'])
  const [selected2faMethod, setSelected2faMethod] = useState<'totp' | 'passkey'>('totp')
  const conditionalPasskeyAbortRef = useRef<AbortController | null>(null)

  const localAuthEnabled = resolveLocalAuthEnabled(oidcConfig, oidcConfigFailed)
  const oidcEnabled = oidcConfig?.enabled === true
  const authConfigLoading = oidcConfig === null && !oidcConfigFailed
  const noAuthMethodConfigured = oidcConfig !== null && !localAuthEnabled && !oidcEnabled
  const showPasskeyLogin = localAuthEnabled && passkeySupported
  const showAuthDivider = localAuthEnabled && (showPasskeyLogin || oidcEnabled)
  const requestedNext = searchParams.get('next')
  const safeNext = requestedNext?.startsWith('/') && !requestedNext.startsWith('//') && !requestedNext.includes('://')
    ? requestedNext
    : '/'

  useEffect(() => {
    setPasskeySupported(isPasskeySupported())
    if (token) {
      navigate('/', { replace: true })
      return
    }
    adminApi.registrationStatus().then(({ enabled }) => {
      setRegistrationEnabled(enabled)
    }).catch(() => {})
    authApi.oidcConfig()
      .then((config) => {
        setOidcConfig(config)
        setOidcConfigFailed(false)
      })
      .catch(() => setOidcConfigFailed(true))
    adminApi.defaultColors().then(({ light, dark }) => {
      setThemeBasedOnSystem(light, dark, resolvedTheme)
    }).catch(() => {})
  }, [navigate, token, resolvedTheme])

  useEffect(() => {
    if (token || (oidcConfig === null && !oidcConfigFailed)) return

    let active = true
    setup.status().then(({ has_users, setup_available }) => {
      if (
        active &&
        !has_users && setup_available !== false &&
        resolveLocalAuthEnabled(oidcConfig, oidcConfigFailed)
      ) {
        navigate('/setup', { replace: true })
      }
    }).catch(() => {})

    return () => {
      active = false
    }
  }, [navigate, oidcConfig, oidcConfigFailed, token])

  useEffect(() => {
    if (
      token ||
      requires2fa ||
      authConfigLoading ||
      !localAuthEnabled ||
      !passkeySupported ||
      isLoading ||
      isPasskeyLoading
    ) return

    const abortController = new AbortController()
    conditionalPasskeyAbortRef.current?.abort()
    conditionalPasskeyAbortRef.current = abortController

    const authenticateConditionally = async () => {
      if (!await isConditionalPasskeySupported() || abortController.signal.aborted) return

      try {
        const options = await authApi.passkeyAuthenticationOptions()
        if (abortController.signal.aborted) return

        const credential = await startConditionalPasskeyAuthentication(
          options.options,
          abortController.signal,
        )
        const result = await authApi.verifyPasskeyAuthentication(options.challenge_id, credential)
        if (abortController.signal.aborted) return

        loginWithToken(result.access_token)
        navigate(safeNext)
      } catch {
        // Conditional UI enhancement dismissed/failed silently
      }
    }

    void authenticateConditionally()

    return () => {
      abortController.abort()
      if (conditionalPasskeyAbortRef.current === abortController) {
        conditionalPasskeyAbortRef.current = null
      }
    }
  }, [
    authConfigLoading,
    isLoading,
    isPasskeyLoading,
    localAuthEnabled,
    loginWithToken,
    navigate,
    passkeySupported,
    requires2fa,
    safeNext,
    token,
  ])

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault()
    conditionalPasskeyAbortRef.current?.abort()
    setError('')
    setIsLoading(true)
    try {
      const result = await login(email, password)
      if (result.requires_2fa) {
        const methods: Array<'totp' | 'passkey'> = result.available_methods?.length ? result.available_methods : ['totp']
        setRequires2fa(true)
        setTempToken(result.temp_token ?? '')
        setAvailable2faMethods(methods)
        setSelected2faMethod(methods.includes('passkey') ? 'passkey' : methods[0])
      } else {
        navigate(safeNext)
      }
    } catch (err) {
      const axiosErr = err as AxiosError
      if (isServerUnreachable(err)) {
        setError(t('auth.serverError'))
      } else if (axiosErr?.response?.status === 429) {
        setError(t('auth.tooManyAttempts'))
      } else {
        setError(t('auth.invalidCredentials'))
      }
    } finally {
      setIsLoading(false)
    }
  }

  const handleOIDCLogin = () => {
    conditionalPasskeyAbortRef.current?.abort()
    window.location.href = '/api/auth/oidc/login'
  }

  const handlePasskeyLogin = async () => {
    conditionalPasskeyAbortRef.current?.abort()
    setError('')
    setIsPasskeyLoading(true)
    try {
      const trimmedEmail = email.trim()
      const options = await authApi.passkeyAuthenticationOptions(trimmedEmail || undefined)
      const credential = await startPasskeyAuthentication(options.options)
      const result = await authApi.verifyPasskeyAuthentication(options.challenge_id, credential)
      loginWithToken(result.access_token)
      navigate(safeNext)
    } catch (err) {
      const axiosErr = err as AxiosError
      if (axiosErr?.response?.status === 429) {
        setError(t('auth.tooManyAttempts'))
      } else {
        setError(t(PASSKEY_LOGIN_FAILURE_KEYS[passkeyFailure(err)]))
      }
    } finally {
      setIsPasskeyLoading(false)
    }
  }

  const handleVerify2fa = async (e: FormEvent) => {
    e.preventDefault()
    setError('')
    setIsLoading(true)
    try {
      await verify2fa(tempToken, totpCode)
      navigate(safeNext)
    } catch (err) {
      const axiosErr = err as AxiosError
      if (isServerUnreachable(err)) {
        setError(t('auth.serverError'))
      } else if (axiosErr?.response?.status === 401) {
        setError(t('auth.invalidCredentials'))
        resetSecondFactor()
      } else {
        setError(t('auth.invalid2faCode'))
      }
    } finally {
      setIsLoading(false)
    }
  }

  function resetSecondFactor() {
    setRequires2fa(false)
    setTempToken('')
    setTotpCode('')
    setAvailable2faMethods(['totp'])
    setSelected2faMethod('totp')
    setError('')
  }

  const handlePasskeySecondFactor = async () => {
    setError('')
    setIsPasskeyLoading(true)
    try {
      const options = await authApi.passkeySecondFactorOptions(tempToken)
      const credential = await startPasskeyAuthentication(options.options)
      const result = await authApi.verifyPasskeySecondFactor(tempToken, options.challenge_id, credential)
      loginWithToken(result.access_token)
      navigate(safeNext)
    } catch (err) {
      const axiosErr = err as AxiosError
      const domErr = err as { name?: string }
      if (domErr?.name === 'NotAllowedError') {
        setError(t('auth.passkeyCancelled'))
      } else if (axiosErr?.response?.status === 401) {
        setError(t('auth.invalidCredentials'))
        resetSecondFactor()
      } else if (axiosErr?.response?.status === 429) {
        setError(t('auth.tooManyAttempts'))
      } else {
        setError(t('auth.passkeyLoginError'))
      }
    } finally {
      setIsPasskeyLoading(false)
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
      authConfigLoading={authConfigLoading}
      oidcConfigFailed={oidcConfigFailed}
      noAuthMethodConfigured={noAuthMethodConfigured}
      localAuthEnabled={localAuthEnabled}
      showAuthDivider={showAuthDivider}
      showPasskeyLogin={showPasskeyLogin}
      handlePasskeyLogin={handlePasskeyLogin}
      isPasskeyLoading={isPasskeyLoading}
      oidcEnabled={oidcEnabled}
      handleOIDCLogin={handleOIDCLogin}
      oidcConfig={oidcConfig}
      registrationEnabled={registrationEnabled}
      selected2faMethod={selected2faMethod}
      setSelected2faMethod={setSelected2faMethod}
      available2faMethods={available2faMethods}
      handlePasskeySecondFactor={handlePasskeySecondFactor}
      passkeySupported={passkeySupported}
    />
  )
}

export default function LoginPage() {
  if (isClerkConfigured) {
    return <ClerkLoginContainer />
  }
  return <LocalLoginContainer />
}
