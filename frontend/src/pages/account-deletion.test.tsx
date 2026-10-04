import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, expect, it, vi } from 'vitest'
import AccountDeletionPage from './account-deletion'
import i18n from '@/lib/i18n'
const get = vi.hoisted(() => vi.fn())
const post = vi.hoisted(() => vi.fn())
const identity = vi.hoisted(() => ({ user: { id: 'user', is_superuser: false } as { id: string; is_superuser: boolean } | null }))
vi.mock('@/lib/api', () => ({ default: { get, post } }))
vi.mock('@/contexts/auth-context', () => ({ useAuth: () => identity }))
const status = { id: 'request-id', state: 'ready', blockers: [], error_code: null, primary_deleted_at: null, completed_at: null, pending_external_count: 3, pending_object_count: 0 }
function mount() { return render(<MemoryRouter><AccountDeletionPage /></MemoryRouter>) }
beforeEach(async () => {
  await i18n.changeLanguage('en'); get.mockReset(); post.mockReset()
  identity.user = { id: 'user', is_superuser: false }
  get.mockImplementation((path: string) => Promise.resolve({ data: path.endsWith('/mine') ? null : { blockers: [], private_workspace_count: 1, preserved_workspace_count: 2, required_operator_steps: 3 } }))
})
it('requires explicit confirmation, shows save-once receipt and avoids premature completion claims', async () => {
  post.mockResolvedValue({ data: { ...status, tracking_token: 'secret-receipt' } })
  mount()
  const button = await screen.findByRole('button', { name: 'Request deletion' })
  expect(button).toBeDisabled()
  fireEvent.change(screen.getByLabelText('Type DELETE MY ACCOUNT to confirm'), { target: { value: 'DELETE MY ACCOUNT' } })
  fireEvent.click(button)
  expect(await screen.findByText(/Save the request ID and secret receipt/)).toBeInTheDocument()
  expect(post).toHaveBeenCalledWith('/account-deletion', { confirmation: 'DELETE MY ACCOUNT' })
  expect(screen.getByLabelText('Secret receipt')).toHaveValue('secret-receipt')
  expect(screen.queryByText('complete')).not.toBeInTheDocument()
  expect(screen.getByText(/Backups remain pending/)).toBeInTheDocument()
})
it('tracks after sign-out without JWT, cookies or secret URL parameters', async () => {
  identity.user = null
  const fetchMock = vi.fn().mockResolvedValue({ ok: true, json: async () => ({ ...status, state: 'backup_expiry_pending' }) })
  vi.stubGlobal('fetch', fetchMock)
  mount()
  fireEvent.change(screen.getByLabelText('Request ID'), { target: { value: 'request-id' } })
  fireEvent.change(screen.getByLabelText('Secret receipt'), { target: { value: 'private-secret' } })
  fireEvent.click(screen.getByRole('button', { name: 'Check deletion status' }))
  await waitFor(() => expect(fetchMock).toHaveBeenCalledWith('/api/account-deletion/request-id/status', {
    headers: { 'X-Deletion-Receipt': 'private-secret' }, credentials: 'omit', cache: 'no-store', redirect: 'error',
  }))
  expect(await screen.findByText('Status: backup_expiry_pending')).toBeInTheDocument()
  expect(get).not.toHaveBeenCalled()
  vi.unstubAllGlobals()
})
it('shows retryable errors without claiming success or saving a phantom receipt', async () => {
  post.mockRejectedValue(new Error('network'))
  mount()
  fireEvent.change(await screen.findByLabelText('Type DELETE MY ACCOUNT to confirm'), { target: { value: 'DELETE MY ACCOUNT' } })
  fireEvent.click(screen.getByRole('button', { name: 'Request deletion' }))
  expect(await screen.findByRole('alert')).toHaveTextContent('Request failed')
  expect(screen.queryByText(/Save the request ID/)).not.toBeInTheDocument()
})
it('renders a separate Hindi interface', async () => {
  await i18n.changeLanguage('hi')
  mount()
  expect(await screen.findByRole('heading', { name: 'व्यक्तिगत खाता हटाएँ' })).toBeInTheDocument()
  expect(screen.queryByText('Delete personal account')).not.toBeInTheDocument()
  expect(screen.queryByText('Request deletion')).not.toBeInTheDocument()
})
