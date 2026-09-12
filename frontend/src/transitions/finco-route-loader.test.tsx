import { act, render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { FinCoRouteLoader } from '@/transitions/finco-route-loader'

describe('FinCoRouteLoader', () => {
  afterEach(() => {
    vi.useRealTimers()
  })

  it('does not flash for a route that resolves inside the delay window', () => {
    vi.useFakeTimers()
    render(
      <MemoryRouter initialEntries={['/transactions']}>
        <FinCoRouteLoader />
      </MemoryRouter>,
    )

    expect(screen.queryByRole('status')).not.toBeInTheDocument()
  })

  it('shows the destination-aware branded loader after 130ms', () => {
    vi.useFakeTimers()
    render(
      <MemoryRouter initialEntries={['/reports']}>
        <FinCoRouteLoader />
      </MemoryRouter>,
    )

    act(() => {
      vi.advanceTimersByTime(130)
    })

    expect(screen.getByRole('status', { name: 'Opening Reports' })).toBeInTheDocument()
    expect(screen.getByText('FinCo-Pilot')).toBeInTheDocument()
    expect(screen.getByText('Preparing Reports')).toBeInTheDocument()
  })

  it('falls back to the brand name for an unknown route', () => {
    vi.useFakeTimers()
    render(
      <MemoryRouter initialEntries={['/something-new']}>
        <FinCoRouteLoader />
      </MemoryRouter>,
    )

    act(() => {
      vi.advanceTimersByTime(130)
    })

    expect(screen.getByRole('status', { name: 'Opening FinCo-Pilot' })).toBeInTheDocument()
  })
})
