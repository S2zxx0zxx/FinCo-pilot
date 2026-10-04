import type { RazorpayConstructor } from '@/types/razorpay'
import { afterEach, expect, it, vi } from 'vitest'

afterEach(() => {
  delete window.Razorpay
  document.querySelectorAll('script[src*="checkout.razorpay.com"]').forEach(node => node.remove())
  vi.useRealTimers()
})

it('does not load on import and shares one explicitly requested checkout load', async () => {
  vi.resetModules()
  const { ensureRazorpaySdk } = await import('./razorpay-sdk')
  expect(document.querySelector('script[src*="checkout.razorpay.com"]')).toBeNull()
  const first = ensureRazorpaySdk()
  expect(ensureRazorpaySdk()).toBe(first)
  const script = document.querySelector<HTMLScriptElement>('script[src*="checkout.razorpay.com"]')!
  expect(script.referrerPolicy).toBe('no-referrer')
  window.Razorpay = vi.fn() as unknown as RazorpayConstructor
  script.dispatchEvent(new Event('load'))
  await first
})

it('permits retry after a failed SDK load', async () => {
  vi.resetModules()
  const { ensureRazorpaySdk } = await import('./razorpay-sdk')
  const first = ensureRazorpaySdk()
  const failure = expect(first).rejects.toThrow('failed to load')
  document.querySelector<HTMLScriptElement>('script[src*="checkout.razorpay.com"]')!.dispatchEvent(new Event('error'))
  await failure
  const retry = ensureRazorpaySdk()
  const success = expect(retry).resolves.toBeUndefined()
  window.Razorpay = vi.fn() as unknown as RazorpayConstructor
  document.querySelector<HTMLScriptElement>('script[src*="checkout.razorpay.com"]')!.dispatchEvent(new Event('load'))
  await success
})
