import { describe, expect, it } from 'vitest'

import { FinCoLogo } from '@/components/finco-logo'
import { renderWithProviders } from '@/test/utils'

describe('FinCoLogo', () => {
  it('renders an svg at the default size', () => {
    const { container } = renderWithProviders(<FinCoLogo />)
    const svg = container.querySelector('svg')!
    expect(svg).toBeInTheDocument()
    expect(svg).toHaveAttribute('width', '24')
    expect(svg).toHaveAttribute('height', '24')
  })

  it('honours an explicit size on both axes', () => {
    const { container } = renderWithProviders(<FinCoLogo size={64} />)
    const svg = container.querySelector('svg')!
    expect(svg).toHaveAttribute('width', '64')
    expect(svg).toHaveAttribute('height', '64')
  })

  it('keeps the traced artwork viewBox so the F mark never distorts', () => {
    const { container } = renderWithProviders(<FinCoLogo size={120} />)
    const svg = container.querySelector('svg')!
    expect(svg).toHaveAttribute('viewBox', '0 0 1000 1000')
    expect(svg).toHaveAttribute('preserveAspectRatio', 'xMidYMid meet')
  })

  it('uses currentColor so it follows the theme', () => {
    const { container } = renderWithProviders(<FinCoLogo />)
    expect(container.querySelector('path')).toHaveAttribute('fill', 'currentColor')
  })

  it('pins white on dark branded surfaces', () => {
    const { container } = renderWithProviders(<FinCoLogo mode="on-dark" />)
    expect(container.querySelector('svg')).toHaveStyle({ color: '#FFFFFF' })
  })

  it('pins black on light branded surfaces', () => {
    const { container } = renderWithProviders(<FinCoLogo mode="on-light" />)
    expect(container.querySelector('svg')).toHaveStyle({ color: '#09090B' })
  })

  it('accepts a className', () => {
    const { container } = renderWithProviders(<FinCoLogo className="text-primary" />)
    expect(container.querySelector('svg')).toHaveClass('text-primary')
  })
})
