import { describe, expect, it } from 'vitest'
import { screen } from '@testing-library/react'
import { PlanBadge } from '@/components/plan-badge'
import { renderWithProviders } from '@/test/utils'

describe('PlanBadge', () => {
  it('renders the purple PRO island with accessible text', () => {
    renderWithProviders(<PlanBadge plan="pro" />)
    const badge = screen.getByLabelText('PRO plan')
    expect(badge).toHaveTextContent('PRO')
    expect(badge).toHaveAttribute('data-plan', 'pro')
    expect(badge).toHaveClass('from-violet-500', 'text-white')
  })

  it('renders the black-gradient MAX island with bold accessible text', () => {
    renderWithProviders(<PlanBadge plan="max" compact />)
    const badge = screen.getByLabelText('MAX plan')
    expect(badge).toHaveTextContent('MAX')
    expect(badge).toHaveAttribute('data-plan', 'max')
    expect(badge).toHaveClass('from-zinc-700', 'font-extrabold', 'text-white')
  })
})
