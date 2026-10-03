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

  it('stays invisible on first paint and uses a short non-blocking pulse on navigation', () => {
    vi.useFakeTimers()
    const { container } = render(
      <MemoryRouter initialEntries={['/']}>
        <Harness />
      </MemoryRouter>,
    )

    expect(container.querySelector('.finco-navigation-pulse')).not.toBeInTheDocument()

    fireEvent.click(screen.getByRole('button', { name: 'Go reports' }))
    act(() => vi.advanceTimersByTime(20))

    const pulse = container.querySelector('.finco-navigation-pulse')
    expect(pulse).toBeInTheDocument()
    expect(container.querySelector('.finco-loading-screen')).not.toBeInTheDocument()

    act(() => vi.advanceTimersByTime(160))
    expect(container.querySelector('.finco-navigation-pulse')).toHaveClass('finco-navigation-pulse--leaving')

    act(() => vi.advanceTimersByTime(90))
    expect(container.querySelector('.finco-navigation-pulse')).not.toBeInTheDocument()
  })
})
