import { beforeEach, describe, expect, it, vi } from 'vitest'
import { screen, waitFor } from '@testing-library/react'
import LoginPage from '@/pages/login'
import LocalUiPreviewPage from '@/pages/local-ui-preview'
import { renderWithProviders, t } from '@/test/utils'

const navigate = vi.hoisted(() => vi.fn())
vi.mock('react-router-dom', async (importOriginal) => ({
  ...(await importOriginal<typeof import('react-router-dom')>()),
  useNavigate: () => navigate,
}))
vi.mock('@/lib/local-ui-preview', () => ({ localUiPreview: true }))
const authContext = vi.hoisted(() => ({
  login: vi.fn(),
  verify2fa: vi.fn(),
  loginWithToken: vi.fn(),
  token: null as string | null,
}))
vi.mock('@/contexts/auth-context', () => ({ useAuth: () => authContext }))
const api = vi.hoisted(() => ({
  setup: { status: vi.fn() },
  auth: { oidcConfig: vi.fn() },
  admin: { registrationStatus: vi.fn(), defaultColors: vi.fn() },
}))
vi.mock('@/lib/api', () => ({
  setup: api.setup,
  auth: api.auth,
  admin: api.admin,
}))
vi.mock('@/lib/webauthn', () => ({
  isPasskeySupported: () => false,
  passkeyFailure: () => 'unknown',
  startPasskeyAuthentication: vi.fn(),
}))
vi.mock('next-themes', () => ({ useTheme: () => ({ resolvedTheme: 'dark' }) }))

beforeEach(() => {
  vi.clearAllMocks()
  authContext.token = null
  api.setup.status.mockResolvedValue({ has_users: true })
  api.auth.oidcConfig.mockResolvedValue({
    enabled: false,
    provider_name: 'OIDC',
    local_auth_enabled: true,
  })
  api.admin.registrationStatus.mockResolvedValue({ enabled: true })
  api.admin.defaultColors.mockResolvedValue({ light: null, dark: null })
})

describe('localhost-only UI preview', () => {
  it('opens visual preview with empty input and does not authenticate', async () => {
    const { user } = renderWithProviders(<LoginPage />, { route: '/login' })
    await user.click(screen.getByRole('button', { name: t('auth.login') }))
    expect(navigate).toHaveBeenCalledWith('/preview')
    expect(authContext.login).not.toHaveBeenCalled()
    expect(api.auth.oidcConfig).not.toHaveBeenCalled()
  })

  it('accepts arbitrary non-email text without authentication', async () => {
    const { user } = renderWithProviders(<LoginPage />, { route: '/login' })
    await user.type(screen.getByLabelText(t('auth.email')), 'random-user')
    await user.type(screen.getByLabelText(t('auth.password')), 'whatever')
    await user.click(screen.getByRole('button', { name: t('auth.login') }))
    expect(navigate).toHaveBeenCalledWith('/preview')
    expect(authContext.login).not.toHaveBeenCalled()
  })

  it('keeps the actual password login path available via auth=real', async () => {
    authContext.login.mockResolvedValue({ requires_2fa: false })
    const { user } = renderWithProviders(<LoginPage />, { route: '/login?auth=real' })
    await screen.findByLabelText(t('auth.email'))
    await user.type(screen.getByLabelText(t('auth.email')), 'someone@example.com')
    await user.type(screen.getByLabelText(t('auth.password')), 'correct-password')
    await user.click(screen.getByRole('button', { name: t('auth.login') }))
    await waitFor(() => expect(authContext.login).toHaveBeenCalledWith('someone@example.com', 'correct-password'))
  })

  it('shows navigation but never loads financial APIs in the preview shell', async () => {
    const { user } = renderWithProviders(<LocalUiPreviewPage />, { route: '/preview' })
    expect(screen.getByText('Preview only.')).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Overview' })).toBeInTheDocument()
    await user.click(screen.getAllByRole('button', { name: 'Budgets' })[0])
    expect(screen.getByRole('heading', { name: 'Budgets' })).toBeInTheDocument()
    expect(api.auth.oidcConfig).not.toHaveBeenCalled()
  })
})
