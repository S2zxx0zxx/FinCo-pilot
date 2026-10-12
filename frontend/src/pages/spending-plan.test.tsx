import { fireEvent, render, screen, waitFor, cleanup } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, beforeEach, expect, it, vi } from 'vitest'
import SpendingPlanPage from './spending-plan'
const mocks = vi.hoisted(() => ({ list: vi.fn(), plan: vi.fn(), workspace: 'one' }))
vi.mock('@/lib/api', () => ({ accounts: { list: mocks.list }, dashboard: { spendingPlan: mocks.plan } }))
vi.mock('@/lib/launch-copy', () => ({ useLaunchText: () => (s: string) => s, useLaunchLocale: () => 'en-IN' }))
vi.mock('@/contexts/workspace-context', () => ({ useWorkspace: () => ({ current: { id: mocks.workspace } }) }))
vi.mock('@/contexts/auth-context', () => ({ useAuth: () => ({ user: { preferences: { currency_display: 'INR' } } }) }))
const cash = { id: 'cash-id', name: 'Cash account', type: 'checking', currency: 'INR', connection_id: null, is_closed: false }
const card = { ...cash, id: 'card-id', name: 'My card', type: 'credit_card' }
const result = { currency: 'INR', as_of: '2026-10-12', through: '2026-11-10', status: 'needs_review', cash_balance: null, card_debt_reserve: null, upcoming_outflows: '0', loan_due_reserve: '0', emergency_buffer: '0', goal_reserve: '0', other_obligations: '0', safe_to_spend: null, daily_allowance: null, shortfall: null, blockers: ['Confirm balances.'], assumptions: [] }
function page() { return <MemoryRouter><SpendingPlanPage /></MemoryRouter> }
beforeEach(() => { vi.resetAllMocks(); mocks.workspace = 'one'; mocks.list.mockResolvedValue([cash, card]); mocks.plan.mockResolvedValue(result) })
afterEach(cleanup)
it('leaves unknown amounts blank and shows unknown totals', async () => {
  render(page())
  expect(await screen.findByLabelText('Cash account · Current cash balance (INR)')).toHaveValue(null)
  await waitFor(() => expect(screen.getByRole('button', { name: 'Calculate spending plan' })).toBeEnabled())
  fireEvent.click(screen.getByRole('button', { name: 'Calculate spending plan' }))
  await screen.findByText('Review needed before an amount is available')
  expect(screen.getAllByText('Unknown — confirmation needed')).toHaveLength(2)
  expect(mocks.plan.mock.calls[0][0].manual_balances).toEqual({})
})
it('sends explicit cash and debt in account currency with current date', async () => {
  render(page())
  fireEvent.change(await screen.findByLabelText('Cash account · Current cash balance (INR)'), { target: { value: '250.25' } })
  fireEvent.change(screen.getByLabelText('My card · Outstanding card debt (INR)'), { target: { value: '200' } })
  fireEvent.click(screen.getByRole('button', { name: 'Calculate spending plan' }))
  await waitFor(() => expect(mocks.plan).toHaveBeenCalledOnce())
  expect(mocks.plan.mock.calls[0][0].manual_balances).toEqual({ 'cash-id': { amount: '250.25', currency: 'INR', kind: 'cash', as_of: new Date().toISOString().slice(0, 10) }, 'card-id': { amount: '200', currency: 'INR', kind: 'card_debt', as_of: new Date().toISOString().slice(0, 10) } })
})
it('discards old balances and results on workspace switch', async () => {
  const view = render(page())
  fireEvent.change(await screen.findByLabelText('Cash account · Current cash balance (INR)'), { target: { value: '250' } })
  fireEvent.click(screen.getByRole('button', { name: 'Calculate spending plan' }))
  await screen.findByText('Review needed before an amount is available')
  mocks.workspace = 'two'; mocks.list.mockResolvedValue([{ ...cash, id: 'other-id', name: 'Other cash' }])
  view.rerender(page())
  expect(await screen.findByLabelText('Other cash · Current cash balance (INR)')).toHaveValue(null)
  expect(screen.queryByText('Review needed before an amount is available')).not.toBeInTheDocument()
})
it('blocks calculation if accounts cannot load', async () => {
  mocks.list.mockRejectedValue(new Error('offline')); render(page())
  await screen.findByRole('alert')
  expect(screen.getByRole('button', { name: 'Calculate spending plan' })).toBeDisabled()
  expect(mocks.plan).not.toHaveBeenCalled()
})
it('prevents edits during a pending calculation', async () => {
  let resolve!: (value: typeof result) => void
  mocks.plan.mockReturnValue(new Promise(r => { resolve = r })); render(page())
  const amount = await screen.findByLabelText('Cash account · Current cash balance (INR)')
  fireEvent.change(amount, { target: { value: '250' } })
  fireEvent.click(screen.getByRole('button', { name: 'Calculate spending plan' }))
  expect(amount).toBeDisabled(); resolve(result)
  await screen.findByText('Review needed before an amount is available')
  expect(amount).toBeEnabled()
})
