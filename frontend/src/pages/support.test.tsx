import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import SupportPage from './support'
import i18n from '@/lib/i18n'

const state = vi.hoisted(() => ({
  user: null as null | { id: string; email: string },
  token: null as string | null,
  info: vi.fn(),
  createTicket: vi.fn(),
}))

vi.mock('@/contexts/auth-context', () => ({
  useAuth: () => ({ user: state.user, token: state.token }),
}))
vi.mock('@/lib/api', () => ({
  support: { info: state.info, createTicket: state.createTicket },
}))
vi.mock('@/lib/build-info', () => ({ APP_VERSION: 'test-version' }))

function mount(route = '/support') {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter initialEntries={[route]}>
        <SupportPage />
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

const supportInfo = {
  enabled: true,
  email: 'support@example.test',
  portal_url: 'https://support.example.test',
  help_center_url: 'https://help.example.test',
  security_url: 'https://security.example.test',
  direct_ticket_submission: true,
  categories: ['account_access', 'billing_payment', 'other'],
}

describe('SupportPage', () => {
  beforeEach(async () => {
    await i18n.changeLanguage('en')
    vi.clearAllMocks()
    state.user = null
    state.token = null
    state.info.mockResolvedValue(supportInfo)
  })

  it('keeps public support and security destinations reachable while logged out', async () => {
    mount()
    expect(await screen.findByText('support@example.test')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /Report a security issue privately/i })).toHaveAttribute(
      'href',
      'https://security.example.test',
    )
    expect(screen.queryByLabelText('Subject')).not.toBeInTheDocument()
  })

  it('submits only bounded user fields plus safe diagnostics when authenticated', async () => {
    state.user = { id: 'user-one', email: 'person@example.test' }
    state.token = 'browser-token-that-must-never-be-in-payload'
    state.createTicket.mockResolvedValue({
      reference: 'FC-ABC123',
      ticket_id: 'ticket-id',
      ticket_number: '10042',
      support_tier: 'priority',
      priority: 'Medium',
    })

    mount('/support?from=%2Fpricing&category=billing_payment&ref=FCREQ-A1B2C3D4E5F6')
    fireEvent.change(await screen.findByLabelText('Subject'), {
      target: { value: 'Payment verification issue' },
    })
    fireEvent.change(screen.getByLabelText('What happened?'), {
      target: { value: 'The payment returned but verification did not complete.' },
    })
    fireEvent.click(screen.getByRole('button', { name: 'Send support request' }))

    await waitFor(() => expect(state.createTicket).toHaveBeenCalledTimes(1))
    expect(state.createTicket).toHaveBeenCalledWith(expect.objectContaining({
      category: 'billing_payment',
      subject: 'Payment verification issue',
      page_path: '/pricing',
      app_version: 'test-version',
      error_reference: 'FCREQ-A1B2C3D4E5F6',
    }))
    const payload = state.createTicket.mock.calls[0][0]
    expect(JSON.stringify(payload)).not.toContain(state.token)
    expect(await screen.findByText('FC-ABC123')).toBeInTheDocument()
  })
})
