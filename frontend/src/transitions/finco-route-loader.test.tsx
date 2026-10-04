import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { describe, expect, it } from 'vitest'
import { FinCoRouteLoader } from '@/transitions/finco-route-loader'

describe('FinCoRouteLoader', () => {
  it('shows genuine Suspense waits immediately without an artificial timer', () => {
    const { container } = render(
      <MemoryRouter initialEntries={['/reports']}>
        <FinCoRouteLoader />
      </MemoryRouter>,
    )

    expect(screen.getByRole('status', { name: 'Opening Reports' })).toBeInTheDocument()
    expect(screen.getByText('FinCo-Pilot')).toBeInTheDocument()
    expect(screen.getByText('Opening Reports')).toBeInTheDocument()
    expect(container.querySelector('.finco-loading-screen__signal')).toBeInTheDocument()
  })

  it('does not render the retired orbit treatment', () => {
    const { container } = render(
      <MemoryRouter initialEntries={['/transactions']}>
        <FinCoRouteLoader />
      </MemoryRouter>,
    )

    expect(container.querySelector('.finco-route-loader__orbit')).not.toBeInTheDocument()
    expect(container.querySelector('.finco-loading-screen__mark')).toBeInTheDocument()
  })

  it('falls back to the brand name for an unknown route', () => {
    render(
      <MemoryRouter initialEntries={['/something-new']}>
        <FinCoRouteLoader />
      </MemoryRouter>,
    )

    expect(screen.getByRole('status', { name: 'Opening FinCo-Pilot' })).toBeInTheDocument()
  })
})
