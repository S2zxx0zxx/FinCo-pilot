import { useRef, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { toast } from 'sonner'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { useAuth } from '@/contexts/auth-context'
import { useBilling } from '@/contexts/billing-context'
import { ensureRazorpaySdk } from '@/lib/razorpay-sdk'
import type { RazorpaySubscriptionCheckoutOptions } from '@/types/razorpay'

interface Quote {
  available: boolean
  plan?: 'pro' | 'max'
  interval?: 'monthly' | 'annual'
  amount_minor?: number
  currency?: string
  subscription_id?: string
  key_id?: string
  total_count?: number
  starts_at?: string
  paid_cycles?: number
}

function validQuote(value: unknown): value is Quote {
  if (!value || typeof value !== 'object') return false
  const row = value as Quote
  return row.available === true && (row.plan === 'pro' || row.plan === 'max')
    && (row.interval === 'monthly' || (row.interval === 'annual' && row.plan === 'pro'))
    && row.currency === 'INR' && Number.isSafeInteger(row.amount_minor) && row.amount_minor! > 0
}

export function RenewalEnrollmentCard() {
  const { token, user } = useAuth()
  const { plan, entitlements, refreshEntitlements } = useBilling()
  const [cycles, setCycles] = useState('')
  const [consent, setConsent] = useState(false)
  const [busy, setBusy] = useState(false)
  const open = useRef(false)
  const eligible = Boolean(token) && (plan !== 'free' || entitlements?.status === 'active')
  const quoteQuery = useQuery({
    queryKey: ['billing', 'renewal', user?.id],
    enabled: eligible,
    retry: false,
    staleTime: 10_000,
    queryFn: async (): Promise<Quote | null> => {
      const result = await fetch('/api/billing/renewal', { headers: { Authorization: `Bearer ${token}` } })
      if (!result.ok) return null
      const body: unknown = await result.json()
      return validQuote(body) ? body : null
    },
  })
  const quote = quoteQuery.data
  if (!eligible || !quote) return null
  const selected = quote.total_count ?? Number(cycles)
  const finite = Number.isSafeInteger(selected) && selected >= 1 && selected <= 120
  const amount = new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 2 }).format(quote.amount_minor! / 100)
  const release = () => { open.current = false; setBusy(false) }

  async function enroll() {
    if (!quote || !consent || !finite || open.current) return
    open.current = true
    setBusy(true)
    try {
      await ensureRazorpaySdk()
      if (!window.Razorpay) throw new Error('Payment checkout is unavailable.')
      const result = await fetch('/api/billing/renewal', {
        method: 'POST', headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
        body: JSON.stringify({ total_count: selected, authorize: true }),
      })
      if (!result.ok) throw new Error('Could not complete renewal setup. Retry the same setup or contact support; do not create another payment.')
      const body: unknown = await result.json()
      if (!validQuote(body) || body.plan !== quote.plan || body.interval !== quote.interval
          || body.amount_minor !== quote.amount_minor || body.total_count !== selected
          || !/^rzp_test_[A-Za-z0-9]+$/.test(body.key_id ?? '')
          || !/^sub_[A-Za-z0-9]{1,100}$/.test(body.subscription_id ?? '')
          || !body.starts_at || !Number.isFinite(Date.parse(body.starts_at))) {
        throw new Error('The renewal quote could not be validated. Contact support before retrying.')
      }
      const options: RazorpaySubscriptionCheckoutOptions = {
        key: body.key_id!, subscription_id: body.subscription_id!, name: 'FinCo-Pilot',
        description: `${selected} renewals at ${amount}/${quote.interval === 'annual' ? 'year' : 'month'}. First cycle ${new Date(body.starts_at).toLocaleDateString()}.`,
        retry: { enabled: false }, modal: { ondismiss: release },
        handler: async (response) => {
          release()
          if (response.razorpay_subscription_id !== body.subscription_id
              || !/^pay_[A-Za-z0-9]{1,100}$/.test(response.razorpay_payment_id)
              || !/^[a-fA-F0-9]{64}$/.test(response.razorpay_signature)) {
            toast.error('Authorization response could not be matched. Contact support.')
            return
          }
          toast.success('Authorization submitted. Access updates after a paid renewal is confirmed.')
          await Promise.allSettled([refreshEntitlements(), quoteQuery.refetch()])
        },
      }
      new window.Razorpay(options).open()
    } catch (error) {
      release()
      toast.error(error instanceof Error ? error.message : 'Renewal setup is unavailable.')
    }
  }

  return <section className="rounded-[26px] border bg-card p-5 sm:p-6" aria-labelledby="renewal-title">
    <h2 id="renewal-title" className="text-lg font-semibold">Renewal setup</h2>
    <p className="mt-2 text-sm text-muted-foreground">Renewals are optional. Your existing paid service is preserved. The recurring price is {amount}/{quote.interval === 'annual' ? 'year' : 'month'}.</p>
    {(quote.paid_cycles ?? 0) > 0 ? <p className="mt-3 text-sm">Confirmed paid renewals: {quote.paid_cycles} of {quote.total_count}. Contact support to change this setup.</p>
      : <div className="mt-4 space-y-3">
        <label className="block text-sm" htmlFor="renewal-cycles">Number of renewals (1–120)</label>
        <Input id="renewal-cycles" type="number" min={1} max={120} value={quote.total_count ?? cycles} readOnly={quote.total_count != null} disabled={busy} onChange={(event) => { setCycles(event.target.value); setConsent(false) }} className="max-w-40" />
        <label className="flex items-start gap-2 text-sm"><input type="checkbox" checked={consent} disabled={busy || !finite} onChange={(event) => setConsent(event.target.checked)} className="mt-1" />I want {finite ? selected : 'the selected number of'} renewals at {amount} each. I will authorize this recurring payment with the provider.</label>
        <p className="text-xs text-muted-foreground">The provider may request a temporary authorization payment. It does not grant renewed access. A new paid cycle must be confirmed before access changes.</p>
        <Button disabled={busy || !consent || !finite} onClick={() => void enroll()}>{busy ? 'Completing setup…' : quote.subscription_id ? 'Resume authorization' : 'Authorize renewals'}</Button>
      </div>}
  </section>
}
