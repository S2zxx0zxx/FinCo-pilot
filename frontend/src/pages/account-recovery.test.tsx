import { beforeEach, expect, it, vi } from 'vitest'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import AccountRecovery from './account-recovery'

const api = vi.hoisted(() => ({ forgotPassword: vi.fn(), resetPassword: vi.fn(), verifyEmail: vi.fn(), requestVerification: vi.fn() }))
vi.mock('@/lib/recovery-api', () => ({ recoveryApi: api }))
beforeEach(() => vi.resetAllMocks())

it('requests recovery without exposing whether an address is registered', async () => {
  api.forgotPassword.mockResolvedValue(null)
  render(<MemoryRouter><AccountRecovery mode="forgot" /></MemoryRouter>)
  fireEvent.change(screen.getByLabelText('Email'), { target: { value: 'user@example.com' } })
  fireEvent.click(screen.getByRole('button', { name: 'Send email' }))
  await waitFor(() => expect(api.forgotPassword).toHaveBeenCalledWith('user@example.com'))
  expect(await screen.findByRole('status')).toHaveTextContent('If this address is eligible')
})

it('does not send mismatched passwords and uses the email token for a valid reset', async () => {
  api.resetPassword.mockResolvedValue(null)
  render(<MemoryRouter initialEntries={['/reset-password?token=email-reset-token']}><AccountRecovery mode="reset" /></MemoryRouter>)
  fireEvent.change(screen.getByLabelText('New password (8–128 characters)'), { target: { value: 'Long-password-1' } })
  fireEvent.change(screen.getByLabelText('Confirm password'), { target: { value: 'Mismatch-123' } })
  fireEvent.click(screen.getByRole('button', { name: 'Change password' }))
  expect(screen.getByRole('alert')).toHaveTextContent('Passwords do not match')
  expect(api.resetPassword).not.toHaveBeenCalled()
  fireEvent.change(screen.getByLabelText('Confirm password'), { target: { value: 'Long-password-1' } })
  fireEvent.click(screen.getByRole('button', { name: 'Change password' }))
  await waitFor(() => expect(api.resetPassword).toHaveBeenCalledWith('email-reset-token', 'Long-password-1'))
  expect(await screen.findByRole('status')).toHaveTextContent('Password changed')
})

it('disables token actions when the email link is incomplete', () => {
  render(<MemoryRouter><AccountRecovery mode="verify" /></MemoryRouter>)
  expect(screen.getByRole('button', { name: 'Verify email' })).toBeDisabled()
  expect(api.verifyEmail).not.toHaveBeenCalled()
})

it('shows an actionable error for an expired verification token', async () => {
  api.verifyEmail.mockRejectedValue(new Error('expired'))
  render(<MemoryRouter initialEntries={['/verify-email?token=expired']}><AccountRecovery mode="verify" /></MemoryRouter>)
  fireEvent.click(screen.getByRole('button', { name: 'Verify email' }))
  expect(await screen.findByRole('alert')).toHaveTextContent('Request a new email')
  expect(screen.getByRole('link', { name: 'Request a new verification link' })).toHaveAttribute('href', '/request-verification')
})
