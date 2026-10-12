import { beforeEach, describe, expect, it, vi } from 'vitest'
import { screen, waitFor } from '@testing-library/react'
import { Route, Routes } from 'react-router-dom'

import { ProtectedRoute } from '@/components/protected-route'
import { renderWithProviders } from '@/test/utils'

const localAuth = vi.hoisted(() => vi.fn())
const clerkAuth = vi.hoisted(() => vi.fn())
const clerkGetToken = vi.hoisted(() => vi.fn())
const loginWithClerk = vi.hoisted(() => vi.fn())

vi.mock('@/contexts/auth-context', () => ({ useAuth: localAuth }))
vi.mock('@/lib/clerk-config', () => ({ isClerkConfigured: true }))
vi.mock('@clerk/clerk-react', () => ({ useAuth: clerkAuth }))

function renderClerkGuard() {
  return renderWithProviders(
    <Routes>
      <Route path="/login" element={<div>login screen</div>} />
      <Route path="/private" element={
        <ProtectedRoute><div>private financial page</div></ProtectedRoute>
      } />
    </Routes>,
    { route: '/private' },
  )
}

beforeEach(() => {
  vi.clearAllMocks()
  localAuth.mockReturnValue({ token: null, isLoading: false, isSessionUnavailable: false, loginWithClerk })
  clerkAuth.mockReturnValue({ isLoaded: true, isSignedIn: true, getToken: clerkGetToken })
})

describe('ClerkProtectedRoute: SSO failure behavior', () => {
  it('surfaces a failed server exchange without leaking private content or repeating the attempt', async () => {
    clerkGetToken.mockResolvedValue('clerk-jwt')
    loginWithClerk.mockRejectedValue({
      response: { status: 503, data: { detail: 'The application is temporarily unavailable.' } },
    })

    renderClerkGuard()

    await waitFor(() => expect(screen.getByText('login screen')).toBeInTheDocument())
    expect(clerkGetToken).toHaveBeenCalledTimes(1)
    expect(loginWithClerk).toHaveBeenCalledTimes(1)
    expect(screen.queryByText('private financial page')).not.toBeInTheDocument()
  })

  it('exits the spinner if Clerk does not return an active session token', async () => {
    clerkGetToken.mockResolvedValue(null)

    renderClerkGuard()

    await waitFor(() => expect(screen.getByText('login screen')).toBeInTheDocument())
    expect(clerkGetToken).toHaveBeenCalledTimes(1)
    expect(loginWithClerk).not.toHaveBeenCalled()
    expect(screen.queryByText('private financial page')).not.toBeInTheDocument()
  })
})
