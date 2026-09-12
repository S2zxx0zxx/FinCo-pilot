import { describe, expect, it } from 'vitest'
import { screen } from '@testing-library/react'
import { PlanBadge } from '@/components/plan-badge'
import { renderWithProviders } from '@/test/utils'

describe('PlanBadge', () => {
  it('renders the PRO island with accessible text', () => {
    renderWithProviders(<PlanBadge plan="pro" />)
    expect(screen.getByLabelText('PRO plan')).toHaveTextContent('PRO')
  })

  it('renders the MAX island with accessible text', () => {
    renderWithProviders(<PlanBadge plan="max" compact />)
    expect(screen.getByLabelText('MAX plan')).toHaveTextContent('MAX')
  })
})
