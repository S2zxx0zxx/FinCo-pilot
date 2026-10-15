import { beforeEach, expect, it, vi } from 'vitest'
import { screen, waitFor } from '@testing-library/react'
import RegisterPage from '@/pages/register'
import { renderWithProviders, t } from '@/test/utils'
const mocks = vi.hoisted(() => ({
  navigate: vi.fn(), loginWithClerk: vi.fn(), signUpWithPassword: vi.fn(),
  verifyEmailCode: vi.fn(), defaultColors: vi.fn(),
}))
vi.mock('react-router-dom', async original => ({
  ...(await original<typeof import('react-router-dom')>()), useNavigate: () => mocks.navigate,
}))
vi.mock('@/lib/clerk-config', () => ({ isClerkConfigured: true }))
vi.mock('@/contexts/auth-context', () => ({ useAuth: () => ({ loginWithClerk: mocks.loginWithClerk }) }))
vi.mock('@/lib/clerk-auth-adapter', () => ({ useClerkCustomAuth: () => ({
  session: null, isLoaded: true, signUpWithPassword: mocks.signUpWithPassword,
  verifyEmailCode: mocks.verifyEmailCode,
}) }))
vi.mock('@/lib/api', () => ({ admin: { defaultColors: mocks.defaultColors }, auth: {} }))
vi.mock('next-themes', () => ({ useTheme: () => ({ resolvedTheme: 'dark' }) }))
beforeEach(() => {
  vi.clearAllMocks()
  mocks.defaultColors.mockResolvedValue({ light: null, dark: null })
})
it('sends incomplete signup to username completion and never attempts a local token exchange', async () => {
  mocks.signUpWithPassword.mockResolvedValue({ status: 'needs_requirements' })
  const { user } = renderWithProviders(<RegisterPage />, { route: '/register' })
  await user.type(await screen.findByLabelText(t('auth.email')), 'new@example.com')
  await user.type(screen.getByLabelText(t('auth.password')), 'sufficient-password')
  await user.type(screen.getByLabelText(t('auth.confirmPassword')), 'sufficient-password')
  await user.click(screen.getByRole('button', { name: t('auth.register') }))
  await waitFor(() => expect(mocks.navigate).toHaveBeenCalledWith('/sign-up#/continue'))
  expect(mocks.loginWithClerk).not.toHaveBeenCalled()
  expect(mocks.navigate).not.toHaveBeenCalledWith('/dashboard')
})
