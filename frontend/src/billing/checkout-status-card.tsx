import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { useAuth } from '@/contexts/auth-context'
import { useBilling } from '@/contexts/billing-context'
import { Button } from '@/components/ui/button'
const messages: Record<string, string> = {
  ready: 'Your existing checkout is ready. Continue with the same plan to resume it.',
  created: 'Your payment is awaiting confirmation. If your bank shows a debit, do not pay again.',
  authorized: 'Payment is authorized; capture is pending. Do not start another payment.',
  failed: 'The provider currently reports a failed attempt. It may still resolve later. If debited, do not pay again; check status or contact support.',
  captured: 'Payment is captured. Access updates after secure payment reconciliation.',
  refund_review: 'The provider reports a refund on this checkout. Check refund status or contact support.',
  expired: 'This checkout window expired. Its provider order is retained; contact support before another payment.',
  unresolved: 'Payment status could not be confirmed. Recheck the existing checkout; do not start another payment.',
}
export function CheckoutStatusCard() {
  const { token, user } = useAuth()
  const { refreshEntitlements, refreshFounderCampaign } = useBilling()
  const query = useQuery({
    queryKey: ['billing', 'checkout-status', user?.id], enabled: Boolean(token), retry: false,
    staleTime: 30_000, refetchOnWindowFocus: false,
    queryFn: async () => {
      const response = await fetch('/api/checkout/status', { headers: { Authorization: `Bearer ${token}` } })
      if (!response.ok) throw new Error('Checkout status unavailable')
      const body = await response.json() as { available?: boolean; checkout?: { state?: string; activation_confirmed?: boolean; test_mode?: boolean } | null }
      if (body.available === false || body.checkout === null) return null
      if (body.available !== true || !body.checkout || body.checkout.test_mode !== true
          || typeof body.checkout.activation_confirmed !== 'boolean' || !Object.hasOwn(messages, body.checkout.state ?? '')) throw new Error('Invalid checkout status')
      return body.checkout
    },
  })
  if (!token || (!query.isError && !query.data)) return null
  async function recheck() {
    await query.refetch()
    await Promise.allSettled([refreshEntitlements(), refreshFounderCampaign()])
  }
  return <section aria-labelledby="checkout-status-title" className="rounded-[26px] border bg-card p-5 sm:p-6">
    <h2 id="checkout-status-title" className="text-lg font-semibold">Checkout status</h2>
    <p className="mt-2 text-xs text-muted-foreground">Test Mode. These observations do not represent a real-money transaction.</p>
    <p role="status" className="mt-3 text-sm">{query.isError ? messages.unresolved : messages[query.data?.state ?? 'unresolved']}</p>
    {query.data?.state === 'captured' && query.data.activation_confirmed && <p className="mt-2 text-sm">Payment reconciliation is recorded. Your current plan and paid dates determine access.</p>}
    <div className="mt-4 flex gap-3"><Button disabled={query.isFetching} onClick={() => void recheck()}>{query.isFetching ? 'Checking…' : 'Check payment status'}</Button><Link to="/support?from=%2Fpricing&category=billing_payment" className="self-center text-sm underline">Contact support</Link></div>
  </section>
}
