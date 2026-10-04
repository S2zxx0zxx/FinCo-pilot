import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, expect, it, vi } from 'vitest'
import WorkspaceDeletionPage from './workspace-deletion'
import i18n from '@/lib/i18n'
const get = vi.hoisted(() => vi.fn())
const post = vi.hoisted(() => vi.fn())
const identity = vi.hoisted(() => ({ user: { id: 'user', is_superuser: false } as { id: string; is_superuser: boolean } | null }))
vi.mock('@/lib/api', () => ({ default: { get, post } }))
vi.mock('@/contexts/auth-context', () => ({ useAuth: () => identity }))
const status = { id: 'request-id', requester_id: 'user', workspace_id: 'workspace-id', state: 'ready', blockers: [], error_code: null, primary_deleted_at: null, completed_at: null, pending_external_count: 3, pending_object_count: 0 }
function mount() { return render(<MemoryRouter><WorkspaceDeletionPage /></MemoryRouter>) }
beforeEach(async () => {
  await i18n.changeLanguage('en'); get.mockReset(); post.mockReset()
  identity.user = { id: 'user', is_superuser: false }
  get.mockImplementation((path: string) => Promise.resolve({ data: path.endsWith('/workspaces') ? [{ id: 'workspace-id', name: 'Business', role: 'owner', is_archived: true }, { id: 'editor-id', name: 'Read only', role: 'editor', is_archived: true }] : path.includes('/mine?') ? null : path.endsWith('/members') ? [] : path.endsWith('/config') ? { enabled: false } : { blockers: [], private_workspace_count: 1, preserved_workspace_count: 0, required_operator_steps: 3 } }))
})
it('requires exact selected workspace and explicit confirmation while preserving global billing', async () => {
  post.mockResolvedValue({ data: { ...status, tracking_token: 'secret-receipt' } })
  mount()
  const select = await screen.findByLabelText('Workspace')
  await screen.findByRole('option', { name: 'Business — workspace-id' })
  expect(screen.queryByRole('option', { name: /Read only/ })).not.toBeInTheDocument()
  fireEvent.change(select, { target: { value: 'workspace-id' } })
  const button = await screen.findByRole('button', { name: 'Request deletion' })
  expect(button).toBeDisabled()
  fireEvent.change(screen.getByLabelText('Type DELETE THIS WORKSPACE to confirm'), { target: { value: 'DELETE THIS WORKSPACE' } })
  fireEvent.click(button)
  expect(await screen.findByText(/Save the request ID and secret receipt/)).toBeInTheDocument()
  expect(post).toHaveBeenCalledWith('/workspace-deletion', { confirmation: 'DELETE THIS WORKSPACE', workspace_id: 'workspace-id' })
  expect(screen.getByText(/global subscription and other workspaces remain/)).toBeInTheDocument()
  expect(screen.queryByText('complete')).not.toBeInTheDocument()
})
it('tracks without JWT, cookies or URL receipt after workspace is gone', async () => {
  identity.user = null
  const fetchMock = vi.fn().mockResolvedValue({ ok: true, json: async () => ({ ...status, state: 'backup_expiry_pending' }) })
  vi.stubGlobal('fetch', fetchMock)
  mount()
  fireEvent.change(screen.getByLabelText('Request ID'), { target: { value: 'request-id' } })
  fireEvent.change(screen.getByLabelText('Secret receipt'), { target: { value: 'private-secret' } })
  fireEvent.click(screen.getByRole('button', { name: 'Check deletion status' }))
  await waitFor(() => expect(fetchMock).toHaveBeenCalledWith('/api/workspace-deletion/request-id/status', { headers: { 'X-Deletion-Receipt': 'private-secret' }, credentials: 'omit', cache: 'no-store', redirect: 'error' }))
  expect(await screen.findByText('Status: backup_expiry_pending')).toBeInTheDocument()
  expect(get).not.toHaveBeenCalled()
  vi.unstubAllGlobals()
})
it('clears a prior target receipt and consent when choosing another workspace', async () => {
  mount()
  await screen.findByRole('option', { name: 'Business — workspace-id' })
  fireEvent.change(screen.getByLabelText('Workspace'), { target: { value: 'workspace-id' } })
  await screen.findByRole('button', { name: 'Request deletion' })
  fireEvent.change(screen.getByLabelText('Secret receipt'), { target: { value: 'old-secret' } })
  fireEvent.change(screen.getByLabelText('Workspace'), { target: { value: '' } })
  await waitFor(() => expect(screen.getByLabelText('Secret receipt')).toHaveValue(''))
  expect(screen.queryByRole('button', { name: 'Request deletion' })).not.toBeInTheDocument()
})
it('renders separate Hindi copy', async () => {
  await i18n.changeLanguage('hi'); mount()
  expect(await screen.findByRole('heading', { name: 'संग्रहीत कार्यक्षेत्र हटाएँ' })).toBeInTheDocument()
  expect(screen.queryByText('Delete archived workspace')).not.toBeInTheDocument()
})
