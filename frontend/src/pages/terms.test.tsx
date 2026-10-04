import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { fireEvent, render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, expect, it, vi } from 'vitest'
import TermsPage from './terms'
import i18n from '@/lib/i18n'

const fetchNotice = vi.hoisted(() => vi.fn())
vi.mock('@/lib/terms', () => ({ fetchTerms: fetchNotice }))
const fixture = {
  version: 'reviewed-version', reviewed_on: '2026-10-04', status: 'draft', effective_date: null,
  operator: { brand_name: 'FinCo-Pilot', legal_name: null, entity_type: 'individual', country_code: 'IN' },
  contact: { name: null, email: null, address: null, phone: null, designation: null, website: null },
  commercial: { refund_policy: { en: null, hi: null }, cancellation_policy: { en: null, hi: null } },
  sections: [{ id: 'scope', title: { en: 'Scope', hi: 'दायरा' }, body: { en: 'Real service scope', hi: 'वास्तविक सेवा का दायरा' } }],
}
function mount() {
  return render(<QueryClientProvider client={new QueryClient()}><MemoryRouter><TermsPage /></MemoryRouter></QueryClientProvider>)
}
beforeEach(async () => { await i18n.changeLanguage('en'); fetchNotice.mockReset() })
it('is public and honest about pending publication, refund decisions and activation', async () => {
  fetchNotice.mockResolvedValue(fixture)
  mount()
  expect(await screen.findByText('Draft — publication pending')).toBeInTheDocument()
  expect(screen.getByText(/Test payment verification does not activate a plan/)).toBeInTheDocument()
  expect(screen.getByText(/Operator refund eligibility/)).toBeInTheDocument()
  expect(screen.getByRole('link', { name: 'Privacy policy' })).toHaveAttribute('href', '/privacy')
  expect(screen.getByRole('link', { name: 'Service and billing help' })).toHaveAttribute('href', '/support?category=billing_payment')
  expect(screen.queryByRole('checkbox')).not.toBeInTheDocument()
})
it('switches to separate Hindi content and commercial decisions', async () => {
  fetchNotice.mockResolvedValue({ ...fixture, commercial: { ...fixture.commercial, refund_policy: { en: 'Reviewed refund decision', hi: 'समीक्षित धनवापसी निर्णय' } } })
  mount()
  await screen.findByText('Real service scope')
  fireEvent.click(screen.getByRole('button', { name: 'हिन्दी' }))
  expect(screen.getByText('वास्तविक सेवा का दायरा')).toBeInTheDocument()
  expect(screen.getByText('समीक्षित धनवापसी निर्णय')).toBeInTheDocument()
  expect(screen.queryByText('Real service scope')).not.toBeInTheDocument()
  expect(screen.queryByText('Reviewed refund decision')).not.toBeInTheDocument()
  expect(screen.getByRole('main')).toHaveAttribute('lang', 'hi')
})
it('renders published facts as text without executing markup', async () => {
  fetchNotice.mockResolvedValue({ ...fixture, status: 'published', effective_date: '2026-10-04', contact: { ...fixture.contact, name: '<script>bad()</script>', email: 'terms@example.com' } })
  mount()
  expect(await screen.findByText('Published terms')).toBeInTheDocument()
  expect(screen.getByText('<script>bad()</script>')).toBeInTheDocument()
  expect(document.querySelector('script')).toBeNull()
  expect(screen.getByRole('link', { name: 'terms@example.com' })).toHaveAttribute('href', 'mailto:terms%40example.com')
})
it('does not claim acceptance on error and recovers through retry', async () => {
  fetchNotice.mockRejectedValue(new Error('unavailable'))
  mount()
  expect(await screen.findByRole('alert', {}, { timeout: 5000 })).toHaveTextContent('Do not assume they are published or accepted')
  fetchNotice.mockResolvedValue(fixture)
  fireEvent.click(screen.getByRole('button', { name: 'Try again' }))
  expect(await screen.findByText('Draft — publication pending')).toBeInTheDocument()
})
