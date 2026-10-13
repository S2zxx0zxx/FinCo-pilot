import { useState, useEffect, useCallback, useRef, type ReactNode } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { auth } from '@/lib/api'
import { SESSION_INVALIDATED_EVENT } from '@/lib/session-state'
import type { User } from '@/types'

import { AuthContext, type LoginResult } from '@/contexts/auth-context'

const normalizeUser = (value: User): User => ({
  ...value,
  preferences: {
    ...(value.preferences ?? {}),
    currency_display: value.preferences?.currency_display || 'INR',
  },
})

// Exclusive to the isolated Docker QA compose stack; never active in production.
const loopbackQa = import.meta.env.DEV && import.meta.env.VITE_LOCAL_QA === 'true' &&
  typeof window !== 'undefined' &&
  window.location.hostname === 'localhost' && window.location.port === '3300'

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [token, setToken] = useState<string | null>(() => loopbackQa ? null : localStorage.getItem('token'))
  const [qaPending, setQaPending] = useState(loopbackQa)
  const [isLoading, setIsLoading] = useState(true)
  const [isSessionUnavailable, setIsSessionUnavailable] = useState(false)
  const queryClient = useQueryClient()
  const clerkExchange = useRef<{ credential: string; promise: Promise<void> } | null>(null)
  const adoptToken = useCallback((accessToken: string) => {
    queryClient.clear()
    setUser(null)
    setIsLoading(true)
    setIsSessionUnavailable(false)
    localStorage.setItem('token', accessToken)
    setToken(accessToken)
  }, [queryClient])

  if (!token && !qaPending && (user !== null || isLoading)) {
    setUser(null)
    setIsLoading(false)
  }

  // The QA-only Node dev server authenticates against the actual, isolated
  // FastAPI instance. Only an ordinary JWT from the existing /auth/login
  // endpoint is accepted; original routes and financial APIs are unchanged.
  useEffect(() => {
    if (!loopbackQa) return
    const controller = new AbortController()
    void fetch('/__qa/session', {
      method: 'POST',
      headers: { 'X-FinCo-QA-Session': '1' },
      cache: 'no-store',
      signal: controller.signal,
    }).then(async response => {
      if (!response.ok) throw new Error('QA session unavailable')
      const payload: unknown = await response.json()
      if (!payload || typeof payload !== 'object' || !('access_token' in payload) ||
        typeof payload.access_token !== 'string' || !payload.access_token) {
        throw new Error('QA session unavailable')
      }
      if (!controller.signal.aborted) adoptToken(payload.access_token)
    }).catch(() => {
      if (!controller.signal.aborted) setIsLoading(false)
    }).finally(() => {
      if (!controller.signal.aborted) setQaPending(false)
    })
    return () => controller.abort()
  }, [adoptToken])

  useEffect(() => {
    if (!token) return
    let cancelled = false
    auth.me()
      .then((me) => {
        if (cancelled || localStorage.getItem('token') !== token) return
        setUser(normalizeUser(me))
        setIsSessionUnavailable(false)
      })
      .catch((error: unknown) => {
        if (cancelled || localStorage.getItem('token') !== token) return
        // Never expose cached financial data without a verified user. A 503 or
        // network outage is NOT evidence of a revoked/expired login session.
        queryClient.clear()
        setUser(null)
        const status = (error as { response?: { status?: number } })?.response?.status
        if (status === 401 || status === 403) {
          localStorage.removeItem('token')
          setToken(null)
          setIsSessionUnavailable(false)
        } else {
          // Keep the opaque credential so an operator can restore the API
          // without forcing the user through Google OAuth again.
          setIsSessionUnavailable(true)
        }
      })
      .finally(() => { if (!cancelled) setIsLoading(false) })
    return () => { cancelled = true }
  }, [token, queryClient])

  // Sync token across tabs via storage events
  useEffect(() => {
    const handleStorage = (e: StorageEvent) => {
      if (e.key === 'token' || e.key === null) {
        queryClient.clear()
        setUser(null)
        setIsSessionUnavailable(false)
        setIsLoading(e.key !== null && e.newValue !== null)
        setToken(e.key === null ? null : e.newValue)
      }
    }
    const handleInvalidation = () => {
      queryClient.clear()
      setUser(null)
      setToken(null)
      setIsSessionUnavailable(false)
    }
    window.addEventListener('storage', handleStorage)
    window.addEventListener(SESSION_INVALIDATED_EVENT, handleInvalidation)
    return () => {
      window.removeEventListener('storage', handleStorage)
      window.removeEventListener(SESSION_INVALIDATED_EVENT, handleInvalidation)
    }
  }, [queryClient])

  const login = useCallback(async (email: string, password: string): Promise<LoginResult> => {
    const data = await auth.login(email, password)

    if (data.requires_2fa) {
      return { requires_2fa: true, temp_token: data.temp_token, available_methods: data.available_methods }
    }

    const accessToken = data.access_token
    adoptToken(accessToken)
    const me = await auth.me()
    if (localStorage.getItem('token') === accessToken) setUser(normalizeUser(me))
    return { requires_2fa: false }
  }, [adoptToken])

  const verify2fa = useCallback(async (tempToken: string, code: string) => {
    const data = await auth.verify2fa(tempToken, code)
    adoptToken(data.access_token)
    const me = await auth.me()
    if (localStorage.getItem('token') === data.access_token) setUser(normalizeUser(me))
  }, [adoptToken])

  const loginWithToken = useCallback((accessToken: string, options?: { preserveCurrentUser: true }) => {
    if (options?.preserveCurrentUser && user) {
      // Only authenticated same-account MFA responses use this path. Keep the
      // recovery-code screen mounted while the cancellable probe revalidates.
      queryClient.clear()
      localStorage.setItem('token', accessToken)
      setToken(accessToken)
    } else {
      adoptToken(accessToken)
    }
  }, [adoptToken, queryClient, user])

  const loginWithClerk = useCallback((clerkToken: string, email?: string, preferences?: Record<string, string>): Promise<void> => {
    // The form and the session effect may complete together. Provision once.
    if (clerkExchange.current?.credential === clerkToken) return clerkExchange.current.promise
    const promise = (async () => {
      const data = await auth.clerkExchange(clerkToken, email, preferences)
      adoptToken(data.access_token)
      if (data.user) {
        setUser(normalizeUser(data.user))
      } else {
        const me = await auth.me()
        setUser(normalizeUser(me))
      }
    })().finally(() => {
      if (clerkExchange.current?.promise === promise) clerkExchange.current = null
    })
    clerkExchange.current = { credential: clerkToken, promise }
    return promise
  }, [adoptToken])

  const updateUser = useCallback((updatedUser: User) => {
    setUser(normalizeUser(updatedUser))
  }, [])

  const confirmEmailVerification = useCallback((userId: string, email: string) => {
    setUser(current => current?.id === userId && current.email === email && token && localStorage.getItem('token') === token
      ? { ...current, is_verified: true } : current)
  }, [token])

  const register = useCallback(async (email: string, password: string, preferences?: Record<string, string>) => {
    await auth.register(email, password, preferences)
    await login(email, password)
  }, [login])

  const logout = useCallback(() => {
    const departingToken = localStorage.getItem('token')
    if (departingToken) void auth.logout(departingToken).catch(() => {
      // Local sign-out still completes offline. Server sessions expire normally
      // if the revocation request cannot reach the server.
    })
    localStorage.removeItem('token')
    setToken(null)
    setUser(null)
    setIsSessionUnavailable(false)
    queryClient.clear()
    if (typeof window !== 'undefined' && (window as unknown as { Clerk?: { signOut: () => Promise<void> } }).Clerk) {
      void (window as unknown as { Clerk: { signOut: () => Promise<void> } }).Clerk.signOut().catch(() => {})
    }
  }, [queryClient])

  return (
    <AuthContext.Provider value={{ user, token, isLoading, isSessionUnavailable, login, verify2fa, loginWithToken, loginWithClerk, register, updateUser, confirmEmailVerification, logout }}>
      {children}
    </AuthContext.Provider>
  )
}
