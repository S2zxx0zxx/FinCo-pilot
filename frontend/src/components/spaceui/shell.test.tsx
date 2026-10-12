import { beforeEach, describe, expect, it, vi } from 'vitest'
import { screen, waitFor } from '@testing-library/react'
import { renderWithProviders } from '@/test/utils'
import { AppLayout } from '@/components/app-layout'

vi.mock('next-themes', () => ({ useTheme: () => ({ resolvedTheme: 'dark', setTheme: vi.fn() }) }))
vi.mock('@/contexts/auth-context', () => ({ useAuth: () => ({
  user: { id: 'qa-user', email: 'qa@example.test', preferences: { onboarding_completed: true, currency_display: 'INR' } },
  logout: vi.fn(), updateUser: vi.fn(),
}) }))
vi.mock('@/contexts/workspace-context', () => ({ useWorkspace: () => ({
  current: { id: 'qa-workspace', name: 'Frontend QA', role: 'owner', kind: 'personal' },
  workspaces: [], hasModule: () => true, isLoading: false, switchWorkspace: vi.fn(), refresh: vi.fn(),
}) }))
vi.mock('@/contexts/collection-filter-context', () => ({ useCollectionFilter: () => ({
  activeAccountIds: null, collections: [], activeCollection: null,
}) }))
vi.mock('@/hooks/use-feature-flags', () => ({ useFeatureFlags: () => ({ agentsEnabled: false }) }))
vi.mock('@/hooks/use-local-auth', () => ({ useLocalAuthEnabled: () => false }))
vi.mock('@/lib/api', () => ({ auth: {}, accounts: { list: async () => [] }, admin: { defaultColors: async () => ({ light: '', dark: '' }) }, workspaces: {} }))
vi.mock('@/components/command-palette', () => ({ CommandPalette: () => null }))
vi.mock('@/components/global-chat-panel', () => ({ GlobalChatPanel: () => null }))
vi.mock('@/components/backup-dialog', () => ({ BackupDialog: () => null }))
vi.mock('@/components/change-password-dialog', () => ({ ChangePasswordDialog: () => null }))
vi.mock('@/components/two-factor-setup', () => ({ TwoFactorSetup: () => null }))
vi.mock('@/components/passkey-management-dialog', () => ({ PasskeyManagementDialog: () => null }))
vi.mock('@/components/update-available-banner', () => ({ UpdateAvailableBanner: () => null }))
vi.mock('@/components/update-available-dialog', () => ({ UpdateAvailableDialog: () => null }))

beforeEach(() => {
  window.matchMedia = vi.fn((query: string) => ({ matches: false, media: query, onchange: null,
    addListener: vi.fn(), removeListener: vi.fn(), addEventListener: vi.fn(), removeEventListener: vi.fn(), dispatchEvent: () => false }))
})

describe('Space UI shell navigation', () => {
  it('opens the mobile drawer, closes on Escape and restores trigger focus', async () => {
    const { user } = renderWithProviders(<AppLayout />)
    const trigger = screen.getByRole('button', { name: 'Navigation' })
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
    await user.click(trigger)
    expect(screen.getByRole('dialog', { name: 'Navigation' })).toBeInTheDocument()
    expect(trigger).toHaveAttribute('aria-expanded', 'true')
    await user.keyboard('{Escape}')
    await waitFor(() => expect(screen.queryByRole('dialog')).not.toBeInTheDocument())
    expect(trigger).toHaveFocus()
  })

  it('renders two independent deletion menu destinations without a Slot crash', async () => {
    const { user } = renderWithProviders(<AppLayout />)
    await user.click(screen.getByRole('button', { name: 'User menu' }))
    expect(screen.getByRole('menuitem', { name: 'Delete archived workspace' })).toHaveAttribute('href', '/workspace-deletion')
    expect(screen.getByRole('menuitem', { name: 'Delete personal account' })).toHaveAttribute('href', '/account-deletion')
  })
})
