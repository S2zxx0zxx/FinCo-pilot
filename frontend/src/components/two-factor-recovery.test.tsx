import { expect, it, vi } from 'vitest'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { TwoFactorSetup } from './two-factor-setup'

const disable = vi.hoisted(() => vi.fn().mockResolvedValue({ detail: '2FA disabled' }))
vi.mock('@/lib/api', () => ({ auth: { disable2fa: disable } }))
vi.mock('@/contexts/auth-context', () => ({ useAuth: () => ({ user: { is_2fa_enabled: true }, updateUser: vi.fn() }) }))
vi.mock('react-i18next', () => ({ useTranslation: () => ({ t: (key: string) => key }) }))

it('accepts a complete unused recovery code when replacing a lost authenticator', async () => {
  render(<TwoFactorSetup open onClose={vi.fn()} />)
  const code = 'abcdef0123456789abcd'
  fireEvent.change(screen.getByLabelText('auth.password'), { target: { value: 'My-password-123' } })
  fireEvent.change(screen.getByLabelText('Authenticator code or unused recovery code'), { target: { value: code } })
  const submit = screen.getByRole('button', { name: 'auth.disable2fa' })
  expect(submit).toBeEnabled()
  fireEvent.click(submit)
  await waitFor(() => expect(disable).toHaveBeenCalledWith('My-password-123', code))
})
