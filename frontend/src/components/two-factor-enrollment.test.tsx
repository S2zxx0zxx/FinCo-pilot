import { expect, it, vi } from 'vitest'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { TwoFactorSetup } from './two-factor-setup'

const enable = vi.hoisted(() => vi.fn().mockResolvedValue({ recovery_codes: ['one-use-code'], access_token: 'fresh-session' }))
const replaceSession = vi.hoisted(() => vi.fn())
vi.mock('@/lib/api', () => ({ auth: {
  setup2fa: vi.fn().mockResolvedValue({ secret: 'synthetic-seed', otpauth_uri: 'otpauth://totp/synthetic' }),
  enable2fa: enable,
} }))
vi.mock('@/contexts/auth-context', () => ({ useAuth: () => ({ user: { is_2fa_enabled: false }, updateUser: vi.fn(), loginWithToken: replaceSession }) }))
vi.mock('react-i18next', () => ({ useTranslation: () => ({ t: (key: string) => key }) }))

it('requires password confirmation and replaces the session after enrollment', async () => {
  render(<TwoFactorSetup open onClose={vi.fn()} />)
  fireEvent.click(screen.getByRole('button', { name: 'auth.enable2fa' }))
  const code = await screen.findByLabelText('auth.twoFactor')
  fireEvent.change(code, { target: { value: '123456' } })
  const submit = screen.getByRole('button', { name: 'auth.verify' })
  expect(submit).toBeDisabled()
  fireEvent.change(screen.getByLabelText('auth.password'), { target: { value: 'synthetic-current-password' } })
  fireEvent.click(submit)
  await waitFor(() => expect(enable).toHaveBeenCalledWith('123456', 'synthetic-current-password'))
  expect(replaceSession).toHaveBeenCalledWith('fresh-session')
  expect(await screen.findByText('Save your recovery codes')).toBeInTheDocument()
})
