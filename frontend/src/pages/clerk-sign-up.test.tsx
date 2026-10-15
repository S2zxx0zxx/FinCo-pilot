import { expect, it, vi } from 'vitest'
import { screen } from '@testing-library/react'
import { Route, Routes } from 'react-router-dom'
import ClerkSignUpPage from '@/pages/clerk-sign-up'
import { renderWithProviders } from '@/test/utils'
const sdk = vi.hoisted(() => ({ configured: true, signUp: vi.fn() }))
vi.mock('@/lib/clerk-config', () => ({ get isClerkConfigured() { return sdk.configured } }))
vi.mock('@clerk/clerk-react', () => ({ SignUp: (props: unknown) => {
  sdk.signUp(props)
  return <div>Required account fields</div>
} }))
it('mounts signup completion outside the protected dashboard with an explicit login destination', () => {
  sdk.configured = true
  renderWithProviders(<ClerkSignUpPage />, { route: '/sign-up#/continue' })
  expect(screen.getByText('Required account fields')).toBeInTheDocument()
  expect(sdk.signUp).toHaveBeenCalledWith({ routing: 'hash', signInUrl: '/login', fallbackRedirectUrl: '/dashboard' })
})
it('keeps local registration available when Clerk is disabled', () => {
  sdk.configured = false
  renderWithProviders(<Routes>
    <Route path="/sign-up" element={<ClerkSignUpPage />} />
    <Route path="/register" element={<div>Local registration</div>} />
  </Routes>, { route: '/sign-up' })
  expect(screen.getByText('Local registration')).toBeInTheDocument()
})
