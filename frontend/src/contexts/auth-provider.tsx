import { useState, useEffect, useCallback, type ReactNode } from 'react'
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

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [token, setToken] = useState<string | null>(() => localStorage.getItem('token'))
  const [isLoading, setIsLoading] = useState(true)
  const queryClient = useQueryClient()
  const adoptToken = useCallback((accessToken: string) => {
    queryClient.clear()
    setUser(null)
    setIsLoading(true)
    localStorage.setItem('token', accessToken)
    setToken(accessToken)
  }, [queryClient])

  if (!token && (user !== null || isLoading)) {
    setUser(null)
    setIsLoading(false)
  }

  useEffect(() => {
    if (!token) return
    let cancelled = false
    auth.me()
      .then((me) => { if (!cancelled && localStorage.getItem('token') === token) setUser(normalizeUser(me)) })
      .catch(() => {
        if (cancelled || localStorage.getItem('token') !== token) return
        queryClient.clear()
        localStorage.removeItem('token')
        setToken(null)
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
        setIsLoading(e.key !== null && e.newValue !== null)
        setToken(e.key === null ? null : e.newValue)
      }
    }
    const handleInvalidation = () => {
      queryClient.clear()
      setUser(null)
      setToken(null)
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

  const updateUser = useCallback((updatedUser: User) => {
    setUser(normalizeUser(updatedUser))
  }, [])

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
    queryClient.clear()
  }, [queryClient])

  return (
    <AuthContext.Provider value={{ user, token, isLoading, login, verify2fa, loginWithToken, register, updateUser, logout }}>
      {children}
    </AuthContext.Provider>
  )
}
