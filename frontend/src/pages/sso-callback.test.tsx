import { StrictMode } from 'react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { screen, waitFor } from '@testing-library/react'
import SSOCallbackPage from '@/pages/sso-callback'
import { renderWithProviders } from '@/test/utils'

const clerk = vi.hoisted(() => ({ loaded: true, handleRedirectCallback: vi.fn() }))
vi.mock('@clerk/clerk-react', () => ({ useClerk: () => clerk }))

beforeEach(() => {
  vi.clearAllMocks()
  clerk.loaded = true
  clerk.handleRedirectCallback.mockResolvedValue(undefined)
})

describe('Google OAuth callback', () => {
  it('does not consume the Google account transfer twice under StrictMode', async () => {
    renderWithProviders(<StrictMode><SSOCallbackPage /></StrictMode>)
    await waitFor(() => expect(clerk.handleRedirectCallback).toHaveBeenCalledTimes(1))
    expect(clerk.handleRedirectCallback).toHaveBeenCalledWith(expect.objectContaining({
      signInUrl: '/login', signUpUrl: '/sign-up', continueSignUpUrl: '/sign-up#/continue',
      signInFallbackRedirectUrl: '/dashboard', signUpFallbackRedirectUrl: '/dashboard',
    }))
  })

  it('waits for Clerk to load before processing the callback', async () => {
    clerk.loaded = false
    const rendered = renderWithProviders(<SSOCallbackPage />)
    expect(clerk.handleRedirectCallback).not.toHaveBeenCalled()
    clerk.loaded = true
    rendered.rerender(<SSOCallbackPage />)
    await waitFor(() => expect(clerk.handleRedirectCallback).toHaveBeenCalledTimes(1))
  })

  it('shows a restart option on an invalid transfer, without a redirect loop or secret error text', async () => {
    clerk.handleRedirectCallback.mockRejectedValue(new Error('account_transfer_invalid sensitive-oauth-data'))
    const rendered = renderWithProviders(<StrictMode><SSOCallbackPage /></StrictMode>)
    expect(await screen.findByRole('alert')).toHaveTextContent('Unable to complete sign-in')
    expect(screen.getByRole('link', { name: 'Return to sign in' })).toHaveAttribute('href', '/login')
    expect(screen.queryByText(/sensitive-oauth-data/)).not.toBeInTheDocument()
    rendered.rerender(<StrictMode><SSOCallbackPage /></StrictMode>)
    expect(clerk.handleRedirectCallback).toHaveBeenCalledTimes(1)
  })
})
