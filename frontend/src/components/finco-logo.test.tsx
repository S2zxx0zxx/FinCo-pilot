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

  it('keeps a fixed viewBox so the mark never distorts', () => {
    const { container } = renderWithProviders(<FinCoLogo size={120} />)
    const svg = container.querySelector('svg')!
    expect(svg).toHaveAttribute('viewBox', '0 0 32 32')
    expect(svg).toHaveAttribute('preserveAspectRatio', 'xMidYMid meet')
  })

  it('uses currentColor so it follows the theme', () => {
    const { container } = renderWithProviders(<FinCoLogo />)
    expect(container.querySelector('path')).toHaveAttribute('stroke', 'currentColor')
  })

  it('accepts a className', () => {
    const { container } = renderWithProviders(<FinCoLogo className="text-primary" />)
    expect(container.querySelector('svg')).toHaveClass('text-primary')
  })
})
