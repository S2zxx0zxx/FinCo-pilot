import { useRef, useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { Button } from '@/components/ui/button'
import { useAuth } from '@/contexts/auth-context'
import { useBilling } from '@/contexts/billing-context'

interface Status { available: true; state: 'available' | 'sending' | 'uncertain' | 'confirmed'; paid_through: string; paid_term_refunded?: boolean }
function valid(value: unknown): value is Status {
  if (!value || typeof value !== 'object') return false
  const row = value as Status
  return row.available === true && ['available', 'sending', 'uncertain', 'confirmed'].includes(row.state)
    && typeof row.paid_through === 'string' && Number.isFinite(Date.parse(row.paid_through))
}

export function CancellationCard() {
  const { token, user } = useAuth()
  const { refreshEntitlements } = useBilling()
  const queryClient = useQueryClient()
  const [consent, setConsent] = useState(false)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const submitting = useRef(false)
  const key = ['billing', 'cancellation', user?.id]
  const status = useQuery({ queryKey: key, enabled: Boolean(token), retry: false,
    queryFn: async (): Promise<Status | null> => {
      const result = await fetch('/api/billing/cancellation', { headers: { Authorization: `Bearer ${token}` } })
      if (!result.ok) return null
      const body: unknown = await result.json()
      return valid(body) ? body : null
    } })
  const row = status.data
  if (!token || !row) return null
  const pending = row.state === 'sending' || row.state === 'uncertain'
  async function cancel() {
    if (submitting.current || (!consent && !pending)) return
    submitting.current = true; setBusy(true); setError('')
    try {
      const result = await fetch('/api/billing/cancellation', { method: 'POST',
        headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
        body: JSON.stringify({ authorize: true }) })
      const body: unknown = result.ok ? await result.json() : null
      if (!valid(body)) throw new Error('Cancellation could not be verified. Check again or contact support.')
      queryClient.setQueryData(key, body)
      await Promise.allSettled([refreshEntitlements(), queryClient.invalidateQueries({ queryKey: ['billing', 'renewal', user?.id] })])
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Cancellation could not be verified. Contact support.')
    } finally { submitting.current = false; setBusy(false) }
  }
  return <section className="rounded-[26px] border bg-card p-5" aria-labelledby="cancellation-title">
    <h2 id="cancellation-title" className="text-lg font-semibold">Stop renewals</h2>
    {row.paid_term_refunded ? <p className="mt-2 text-sm">This paid term was fully refunded. Refunds do not themselves stop future renewal collection.</p> : <p className="mt-2 text-sm">Your confirmed paid service ends {new Date(row.paid_through).toLocaleString()}. Cancellation preserves that paid service and does not issue a refund.</p>}
    {row.state === 'confirmed' ? <p role="status" className="mt-3 text-sm">Renewals are canceled. {row.paid_term_refunded ? 'The fully refunded term no longer grants paid access.' : 'Your paid service remains available until its end date.'}</p>
      : <div className="mt-3 space-y-3">
        {pending ? <p role="status">Cancellation is awaiting provider confirmation. Check again or contact support.</p>
          : <label className="flex items-start gap-2 text-sm"><input type="checkbox" checked={consent} disabled={busy} onChange={event => setConsent(event.target.checked)} />I authorize stopping future renewals. This renewal setup cannot be reactivated.</label>}
        <Button disabled={busy || (!consent && !pending)} onClick={() => void cancel()}>{busy ? 'Checking…' : pending ? 'Check cancellation' : 'Cancel renewals'}</Button>
      </div>}
    {error && <p role="alert" className="mt-3 text-sm">{error}</p>}
  </section>
}
