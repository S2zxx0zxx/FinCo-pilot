import { beforeEach, expect, it, vi } from 'vitest'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router-dom'
import LoansPage from './loans'

const state = vi.hoisted(() => ({
  workspace: { current: { id: 'workspace-one', default_currency: 'INR' }, canWrite: true },
  api: { list: vi.fn(), create: vi.fn(), get: vi.fn(), update: vi.fn() },
}))
vi.mock('@/lib/api', () => ({ loans: state.api }))
vi.mock('@/contexts/workspace-context', () => ({ useWorkspace: () => state.workspace }))

const loan = {
  id: 'loan-one', name: 'Home loan', principal: '1200.00', annual_rate: '0',
  term_months: 12, first_due_date: '2026-01-31', currency: 'INR',
  paid_installments: 0, version: 1, archived: false, updated_at: '2026-09-20T10:00:00Z',
}
const detail = {
  loan, monthly_payment: '100.00', total_interest: '0.00', remaining_principal: '1200.00',
  schedule: [{ number: 1, due_date: '2026-01-31', payment: '100.00', principal: '100.00', interest: '0.00', remaining_principal: '1100.00', reported_paid: false }],
}
function mount() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(<QueryClientProvider client={client}><MemoryRouter><LoansPage /></MemoryRouter></QueryClientProvider>)
}
beforeEach(() => {
  vi.resetAllMocks()
  state.workspace = { current: { id: 'workspace-one', default_currency: 'INR' }, canWrite: true }
  state.api.list.mockResolvedValue([loan])
  state.api.get.mockResolvedValue(detail)
})

it('shows a real schedule with self-reported status and reserves disclosure', async () => {
  mount()
  fireEvent.click(await screen.findByRole('button', { name: 'Home loan' }))
  expect(await screen.findByRole('table')).toHaveTextContent('Not reported paid')
  expect(screen.getByText(/conservatively reserved twice/)).toBeInTheDocument()
  expect(screen.getByRole('link', { name: 'Open safe-to-spend plan' })).toHaveAttribute('href', '/spending-plan')
})

it('keeps workspace viewers read-only', async () => {
  state.workspace.canWrite = false
  mount()
  fireEvent.click(await screen.findByRole('button', { name: 'Home loan' }))
  await screen.findByRole('table')
  expect(screen.queryByRole('button', { name: 'Save loan plan' })).not.toBeInTheDocument()
  expect(screen.queryByRole('button', { name: 'Update reported status' })).not.toBeInTheDocument()
})

it('requires confirmation and sends the displayed version with a payment update', async () => {
  state.api.update.mockResolvedValue({ ...loan, paid_installments: 2, version: 2 })
  mount()
  fireEvent.click(await screen.findByRole('button', { name: 'Home loan' }))
  const save = await screen.findByRole('button', { name: 'Update reported status' })
  expect(save).toBeDisabled()
  fireEvent.change(screen.getByLabelText('Consecutive full installments paid (from installment 1)'), { target: { value: '2' } })
  fireEvent.click(screen.getByLabelText(/I checked my lender/))
  fireEvent.click(save)
  await waitFor(() => expect(state.api.update).toHaveBeenCalledWith('loan-one', { version: 1, paid_installments: 2, archived: false }))
})

it('clears the selected loan when switching workspaces', async () => {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  const page = () => <QueryClientProvider client={client}><MemoryRouter><LoansPage /></MemoryRouter></QueryClientProvider>
  const view = render(page())
  fireEvent.click(await screen.findByRole('button', { name: 'Home loan' }))
  await screen.findByRole('table')
  state.workspace.current = { id: 'workspace-two', default_currency: 'INR' }
  state.api.list.mockResolvedValue([])
  view.rerender(page())
  expect(await screen.findByText('No loan plans in this workspace yet.')).toBeInTheDocument()
  expect(screen.queryByRole('table')).not.toBeInTheDocument()
})

it('does not invent an empty result after a load failure', async () => {
  state.api.list.mockRejectedValue(new Error('offline'))
  mount()
  expect(await screen.findByRole('alert')).toHaveTextContent('Loan plans could not be loaded.')
  expect(screen.queryByText('No loan plans in this workspace yet.')).not.toBeInTheDocument()
  expect(screen.getByRole('button', { name: 'Save loan plan' })).toBeDisabled()
})
