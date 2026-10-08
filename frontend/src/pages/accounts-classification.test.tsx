import { expect, it, vi } from 'vitest'
import { fireEvent, render, screen } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { AccountDialog } from './accounts'
import type { Account } from '@/types'

vi.mock('@/contexts/auth-context', () => ({ useAuth: () => ({ user: { preferences: { currency_display: 'USD' } } }) }))
vi.mock('@/lib/api', () => ({ accounts: {}, connections: {}, currencies: { list: async () => [] } }))

function mount(type: string, provider = 'simplefin') {
  const save = vi.fn()
  const account = { id: 'account-1', connection_id: 'connection-1', name: 'Bank account', type, provider, balance: -500, currency: 'USD' } as Account
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  render(<QueryClientProvider client={client}><AccountDialog open onClose={() => {}} account={account} onSave={save} loading={false} /></QueryClientProvider>)
  return save
}

it('allows an unknown account to be renamed without submitting a fabricated cash type', () => {
  const save = mount('unknown')
  expect(screen.getByRole('combobox')).toHaveValue('unknown')
  expect(screen.getByText(/SimpleFIN does not supply account types/)).toBeInTheDocument()
  fireEvent.click(screen.getByRole('button', { name: 'Save' }))
  expect(save).toHaveBeenCalledWith({ display_name: null })
})

it('submits an explicit loan classification and allows its later correction', () => {
  const save = mount('loan')
  expect(screen.getByRole('combobox')).toBeEnabled()
  fireEvent.click(screen.getByRole('button', { name: 'Save' }))
  expect(save).toHaveBeenLastCalledWith({ type: 'loan', display_name: null })
  fireEvent.change(screen.getByRole('combobox'), { target: { value: 'checking' } })
  fireEvent.click(screen.getByRole('button', { name: 'Save' }))
  expect(save).toHaveBeenLastCalledWith({ type: 'checking', display_name: null })
})

it('retains provider ownership of Enable Banking loans', () => {
  const save = mount('loan', 'enable_banking')
  expect(screen.getByRole('combobox')).toBeDisabled()
  fireEvent.click(screen.getByRole('button', { name: 'Save' }))
  expect(save).toHaveBeenCalledWith({ display_name: null })
})
