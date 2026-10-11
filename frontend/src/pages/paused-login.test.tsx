import { describe, expect, it, vi } from 'vitest'
import { screen, render } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { ProtectedRoute } from '@/components/protected-route'
import LocalUiPreviewPage from '@/pages/local-ui-preview'
import { renderWithProviders } from '@/test/utils'

vi.mock('@/lib/local-ui-preview', () => ({
  loginPaused: true,
  localUiPreview: false,
  uiPreviewAvailable: true,
}))
vi.mock('@/contexts/auth-context', () => ({
  useAuth: () => ({ token: null, user: null, isLoading: false }),
}))

describe('temporary public preview while login is paused', () => {
  it('shows the public UI without a login button or live financial data', async () => {
    const { user } = renderWithProviders(<LocalUiPreviewPage />, { route: '/' })
    expect(screen.getByRole('heading', { name: 'Overview' })).toBeInTheDocument()
    expect(screen.getByText('Sign-in is temporarily paused.', { exact: false })).toBeInTheDocument()
    expect(screen.queryByRole('link', { name: 'Real sign in' })).not.toBeInTheDocument()
    expect(screen.getAllByText('No data connected').length).toBeGreaterThan(0)

    await user.click(screen.getAllByRole('button', { name: 'Accounts' })[0])
    expect(screen.getByRole('heading', { name: 'Accounts' })).toBeInTheDocument()
  })

  it('does not render protected financial pages for unsigned visitors', async () => {
    render(
      <MemoryRouter initialEntries={['/accounts']}>
        <Routes>
          <Route path="/accounts" element={
            <ProtectedRoute><div>Confidential account data</div></ProtectedRoute>
          } />
          <Route path="/" element={<div>Public preview home</div>} />
        </Routes>
      </MemoryRouter>,
    )
    expect(await screen.findByText('Public preview home')).toBeInTheDocument()
    expect(screen.queryByText('Confidential account data')).not.toBeInTheDocument()
  })
})
