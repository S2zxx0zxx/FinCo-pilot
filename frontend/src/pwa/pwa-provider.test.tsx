import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { PWAProvider, usePWA } from '@/pwa/pwa-provider'

function Probe() {
  const { isOnline, canInstall, install } = usePWA()
  return (
    <div>
      <span data-testid="network">{isOnline ? 'online' : 'offline'}</span>
      <span data-testid="installable">{canInstall ? 'yes' : 'no'}</span>
      <button type="button" onClick={() => void install()}>install</button>
    </div>
  )
}

describe('PWAProvider', () => {
  it('tracks browser online/offline events without touching finance data', () => {
    render(<PWAProvider><Probe /></PWAProvider>)

    fireEvent(window, new Event('offline'))
    expect(screen.getByTestId('network')).toHaveTextContent('offline')

    fireEvent(window, new Event('online'))
    expect(screen.getByTestId('network')).toHaveTextContent('online')
  })

  it('captures the native install prompt and invokes it on demand', async () => {
    const prompt = vi.fn().mockResolvedValue(undefined)
    const event = new Event('beforeinstallprompt') as Event & {
      prompt: () => Promise<void>
      userChoice: Promise<{ outcome: 'accepted'; platform: string }>
    }
    event.prompt = prompt
    event.userChoice = Promise.resolve({ outcome: 'accepted', platform: 'web' })

    render(<PWAProvider><Probe /></PWAProvider>)
    fireEvent(window, event)

    expect(screen.getByTestId('installable')).toHaveTextContent('yes')
    fireEvent.click(screen.getByRole('button', { name: 'install' }))

    await waitFor(() => expect(prompt).toHaveBeenCalledTimes(1))
    await waitFor(() => expect(screen.getByTestId('installable')).toHaveTextContent('no'))
  })
})
