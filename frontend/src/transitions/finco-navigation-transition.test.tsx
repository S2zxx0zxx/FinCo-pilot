import { act, fireEvent, render, screen } from '@testing-library/react'
import { MemoryRouter, useNavigate } from 'react-router-dom'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { FinCoNavigationTransition } from '@/transitions/finco-navigation-transition'

function Harness() {
  const navigate = useNavigate()
  return (
    <>
      <button type="button" onClick={() => navigate('/reports')}>Go reports</button>
      <FinCoNavigationTransition />
    </>
  )
}

describe('FinCoNavigationTransition', () => {
  afterEach(() => {
    vi.useRealTimers()
  })

  it('stays invisible on first paint and animates a real section change', () => {
    vi.useFakeTimers()
    render(
      <MemoryRouter initialEntries={['/']}>
        <Harness />
      </MemoryRouter>,
    )

    expect(screen.queryByRole('status')).not.toBeInTheDocument()

    fireEvent.click(screen.getByRole('button', { name: 'Go reports' }))
    expect(screen.getByRole('status', { name: 'Opening Reports' })).toBeInTheDocument()
    expect(screen.getByText('Preparing Reports')).toBeInTheDocument()

    act(() => vi.advanceTimersByTime(360))
    expect(screen.getByRole('status', { name: 'Opening Reports' })).toHaveClass('finco-route-loader--leaving')

    act(() => vi.advanceTimersByTime(180))
    expect(screen.queryByRole('status')).not.toBeInTheDocument()
  })
})
