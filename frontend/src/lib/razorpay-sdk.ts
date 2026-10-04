import type { RazorpayConstructor } from '@/types/razorpay'

let pending: Promise<void> | undefined

/** Load checkout only on an explicit payment action, never on recovery pages. */
export function ensureRazorpaySdk(): Promise<void> {
  const loaded: RazorpayConstructor | undefined = window.Razorpay
  if (loaded) return Promise.resolve()
  if (pending) return pending
  pending = new Promise<void>((resolve, reject) => {
    const script = document.createElement('script')
    const finish = (error?: Error) => {
      window.clearTimeout(timer)
      script.onload = null
      script.onerror = null
      if (error) {
        script.remove()
        pending = undefined
        reject(error)
      } else resolve()
    }
    const timer = window.setTimeout(() => finish(new Error('Payment SDK timed out')), 15000)
    script.src = 'https://checkout.razorpay.com/v1/checkout.js'
    script.async = true
    script.referrerPolicy = 'no-referrer'
    script.onload = () => finish(window.Razorpay ? undefined : new Error('Payment SDK unavailable'))
    script.onerror = () => finish(new Error('Payment SDK failed to load'))
    document.head.appendChild(script)
  })
  return pending
}
