import { act, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, beforeEach, expect, it, vi } from 'vitest'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router-dom'
import i18n from '@/lib/i18n'
import { translateLaunch } from '@/lib/launch-copy'
import AccountRecovery from './account-recovery'
import LoansPage from './loans'
import SpendingPlanPage from './spending-plan'

const api = vi.hoisted(() => ({ forgotPassword: vi.fn(), list: vi.fn(), spendingPlan: vi.fn() }))
vi.mock('@/lib/recovery-api', () => ({ recoveryApi: api }))
vi.mock('@/lib/api', () => ({ loans: { list: api.list }, dashboard: { spendingPlan: api.spendingPlan } }))
vi.mock('@/contexts/workspace-context', () => ({ useWorkspace: () => ({ current: { id: 'one', default_currency: 'INR' }, canWrite: false }) }))
vi.mock('@/contexts/auth-context', () => ({ useAuth: () => ({ user: { preferences: { currency_display: 'INR' } } }) }))

beforeEach(async () => {
  vi.resetAllMocks()
  await i18n.changeLanguage('hi')
  api.list.mockResolvedValue([])
})
afterEach(async () => { await i18n.changeLanguage('en') })

it('uses Hindi throughout recovery without exposing account existence', async () => {
  api.forgotPassword.mockResolvedValue(null)
  render(<MemoryRouter><AccountRecovery mode="forgot" /></MemoryRouter>)
  expect(screen.getByRole('heading')).toHaveTextContent('पासवर्ड भूल गए?')
  fireEvent.change(screen.getByLabelText('ईमेल'), { target: { value: 'user@example.com' } })
  fireEvent.click(screen.getByRole('button', { name: 'ईमेल भेजें' }))
  expect(await screen.findByRole('status')).toHaveTextContent('यदि यह ईमेल पता योग्य है')
  expect(api.forgotPassword).toHaveBeenCalledWith('user@example.com')
})

it('reacts to language changes and keeps loan viewers read-only', async () => {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  render(<QueryClientProvider client={client}><MemoryRouter><LoansPage /></MemoryRouter></QueryClientProvider>)
  expect(await screen.findByText('इस वर्कस्पेस में अभी कोई लोन योजना नहीं है।')).toBeInTheDocument()
  expect(screen.getByRole('heading')).toHaveTextContent('लोन और EMI योजनाएँ')
  expect(screen.queryByRole('button', { name: 'लोन योजना सेव करें' })).not.toBeInTheDocument()
  await act(async () => { await i18n.changeLanguage('en') })
  expect(screen.getByRole('heading')).toHaveTextContent('Loans and EMI plans')
})

it('localises spending-plan labels and connection failure feedback', async () => {
  api.spendingPlan.mockRejectedValue(new Error('offline'))
  render(<MemoryRouter><SpendingPlanPage /></MemoryRouter>)
  expect(screen.getByLabelText('कितने दिनों की योजना बनाएँ?')).toHaveValue(30)
  fireEvent.click(screen.getByRole('button', { name: 'खर्च की योजना बनाएँ' }))
  expect(await screen.findByRole('alert')).toHaveTextContent('इंटरनेट कनेक्शन जाँचकर फिर कोशिश करें')
})

it('preserves account names in translated bank blockers and falls back for new server messages', () => {
  expect(translateLaunch('Safe-to-spend is unavailable for My Bank: this bank connection does not yet reliably distinguish cash from loan accounts.', 'hi-IN')).toContain('My Bank')
  expect(translateLaunch('A recent exchange rate for USD/INR is unavailable.', 'hi')).toContain('USD/INR')
  expect(translateLaunch('New server error', 'hi')).toBe('New server error')
})
