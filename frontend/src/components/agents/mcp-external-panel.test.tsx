import { beforeEach, expect, it, vi } from 'vitest'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { McpExternalPanel } from './mcp-external-panel'

const api = vi.hoisted(() => ({ info: vi.fn(), mcpTokens: { list: vi.fn(), approvals: vi.fn(), decide: vi.fn(), revoke: vi.fn(), create: vi.fn() } }))
vi.mock('@/lib/api', () => ({ agents: api }))
vi.mock('@/contexts/workspace-context', () => ({ useWorkspace: () => ({ current: { id: 'workspace-one' } }) }))
vi.mock('react-i18next', () => ({ useTranslation: () => ({ t: (_key: string, fallback: string) => fallback }) }))

beforeEach(() => {
  vi.resetAllMocks()
  api.info.mockResolvedValue({ external_mcp_url: 'https://example.com/mcp' })
  api.mcpTokens.list.mockResolvedValue([])
  api.mcpTokens.approvals.mockResolvedValue([{ id: 'approval-one', tool: 'propose_create_transaction', arguments: { amount: 1250, type: 'debit', description: 'Rent', apply: true }, status: 'pending', expires_at: '2099-01-01T00:00:00Z' }])
  api.mcpTokens.decide.mockResolvedValue({ status: 'executed' })
})

it('shows exact proposed values and waits for an explicit approval click', async () => {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  render(<QueryClientProvider client={client}><McpExternalPanel /></QueryClientProvider>)
  const approve = await screen.findByRole('button', { name: 'Approve this exact action' })
  expect(screen.getByText(/"amount": 1250/)).toHaveTextContent('Rent')
  expect(api.mcpTokens.decide).not.toHaveBeenCalled()
  fireEvent.click(approve)
  await waitFor(() => expect(api.mcpTokens.decide).toHaveBeenCalledWith('approval-one', 'approve'))
})

it('rejects without submitting approval', async () => {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  render(<QueryClientProvider client={client}><McpExternalPanel /></QueryClientProvider>)
  fireEvent.click(await screen.findByRole('button', { name: 'Reject' }))
  await waitFor(() => expect(api.mcpTokens.decide).toHaveBeenCalledWith('approval-one', 'reject'))
})

it('shows expired and credential-changed tokens truthfully with recreation guidance', async () => {
  api.mcpTokens.list.mockResolvedValue([
    { id: 'old', allow_writes: false, revoked: false, expires_at: '2099-01-01T00:00:00Z', status: 'credential_changed' },
    { id: 'expired', allow_writes: false, revoked: false, expires_at: '2000-01-01T00:00:00Z', status: 'expired' },
  ])
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  render(<QueryClientProvider client={client}><McpExternalPanel /></QueryClientProvider>)
  expect(await screen.findByText(/Recreate required/)).toBeInTheDocument()
  expect(screen.getByText(/· Expired/)).toBeInTheDocument()
  expect(screen.getByText(/Old unregistered tokens must be replaced/)).toBeInTheDocument()
})

it('creates an explicit HTTP client config with a read-only token', async () => {
  api.mcpTokens.create.mockResolvedValue({ token: 'synthetic-external-token', expires_in_days: 30 })
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  const { container } = render(<QueryClientProvider client={client}><McpExternalPanel /></QueryClientProvider>)
  fireEvent.click(await screen.findByRole('button', { name: 'Generate token' }))
  await waitFor(() => expect(api.mcpTokens.create).toHaveBeenCalledWith(false))
  await waitFor(() => expect(container.textContent).toContain('"type": "http"'))
  const configuration = [...container.querySelectorAll('pre')].find(node => node.textContent?.includes('"mcpServers"'))
  const parsed = JSON.parse(configuration!.textContent!)
  expect(parsed.mcpServers.fincopilot).toEqual({ type: 'http', url: 'https://example.com/mcp', headers: { Authorization: 'Bearer synthetic-external-token' } })
})
