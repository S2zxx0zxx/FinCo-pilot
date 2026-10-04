import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { fireEvent, render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, expect, it, vi } from 'vitest'
import PrivacyPage from './privacy'
import i18n from '@/lib/i18n'
import type { PrivacyPolicy } from '@/lib/privacy-policy'

const fetchPolicy = vi.hoisted(() => vi.fn())
vi.mock('@/lib/privacy-policy', () => ({ fetchPrivacyPolicy: fetchPolicy }))
const policy: PrivacyPolicy = {
  version: 'reviewed-version', reviewed_on: '2026-10-04', status: 'draft', effective_date: null,
  operator: { brand_name: 'FinCo-Pilot', legal_name: null, entity_type: 'individual', country_code: 'IN' },
  contact: { name: null, email: null, address: null }, deployment: { providers: null, locations: null },
  sections: [{ id: 'scope', title: { en: 'Scope', hi: 'दायरा' }, body: { en: 'Real scope', hi: 'वास्तविक दायरा' } }],
}
function mount() {
  return render(<QueryClientProvider client={new QueryClient()}><MemoryRouter><PrivacyPage /></MemoryRouter></QueryClientProvider>)
}
beforeEach(async () => { await i18n.changeLanguage('en'); fetchPolicy.mockReset() })
it('shows an honest draft while logged out and switches the entire notice to Hindi', async () => {
  fetchPolicy.mockResolvedValue(policy)
  mount()
  expect(await screen.findByText('Draft — publication pending')).toBeInTheDocument()
  expect(screen.queryByText('Published policy')).not.toBeInTheDocument()
  expect(screen.getByRole('link', { name: 'Privacy help' })).toHaveAttribute('href', '/support?category=privacy_data')
  fireEvent.click(screen.getByRole('button', { name: 'हिन्दी' }))
  expect(screen.getByText('वास्तविक दायरा')).toBeInTheDocument()
  expect(screen.getByRole('main')).toHaveAttribute('lang', 'hi')
})
it('renders operator text safely and an explicit published date', async () => {
  fetchPolicy.mockResolvedValue({ ...policy, status: 'published', effective_date: '2026-10-04',
    contact: { ...policy.contact, name: '<script>bad()</script>', email: 'privacy@example.com' } })
  mount()
  expect(await screen.findByText('Published policy')).toBeInTheDocument()
  expect(screen.getByText('<script>bad()</script>')).toBeInTheDocument()
  expect(document.querySelector('script')).toBeNull()
  expect(screen.getByRole('link', { name: 'privacy@example.com' })).toHaveAttribute('href', 'mailto:privacy%40example.com')
})
it('shows an unavailable notice and can retry without treating it as published', async () => {
  fetchPolicy.mockRejectedValue(new Error('unavailable'))
  mount()
  expect(await screen.findByRole('alert', {}, { timeout: 5000 })).toHaveTextContent('Do not assume it is published')
  fetchPolicy.mockResolvedValue(policy)
  fireEvent.click(screen.getByRole('button', { name: 'Try again' }))
  expect(await screen.findByText('Draft — publication pending')).toBeInTheDocument()
})
