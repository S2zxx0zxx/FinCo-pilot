import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { useAuth } from '@/contexts/auth-context'
import { Button } from '@/components/ui/button'
interface Refund { id: string; state: 'sending' | 'uncertain' | 'pending' | 'processed' | 'failed'; amount_minor: number; currency: 'INR' }
const states = {
  sending: 'Awaiting provider confirmation. Contact support before retrying.',
  uncertain: 'Outcome unknown. Support must reconcile the existing refund.',
  pending: 'Provider is processing the refund. Bank credit is not yet confirmed.',
  processed: 'Provider reports the refund processed. Bank credit timing can vary.',
  failed: 'Provider reports the refund failed. Contact support for review.',
}
function validRows(value: unknown): value is Refund[] {
  return Array.isArray(value) && value.every(item => item && typeof item.id === 'string'
    && Object.hasOwn(states, item.state) && Number.isSafeInteger(item.amount_minor) && item.amount_minor > 0 && item.currency === 'INR')
}
export function RefundsCard() {
  const { token, user } = useAuth()
  const query = useQuery({ queryKey: ['billing', 'refunds', user?.id], enabled: Boolean(token), retry: false,
    queryFn: async (): Promise<Refund[] | null> => {
      const response = await fetch('/api/billing/refunds', { headers: { Authorization: `Bearer ${token}` } })
      if (!response.ok) throw new Error('Refund status is unavailable. Contact support.')
      const data: unknown = await response.json()
      if (!data || typeof data !== 'object') throw new Error('Refund status is unavailable. Contact support.')
      const row = data as { available?: unknown; refunds?: unknown; provider_refunds?: unknown }
      if (row.available === false) return null
      if (row.available !== true || !validRows(row.refunds) || !validRows(row.provider_refunds)) throw new Error('Refund status is unavailable. Contact support.')
      return [...row.refunds, ...row.provider_refunds]
    } })
  if (!token || query.isPending || query.data === null) return null
  return <section className="rounded-[26px] border bg-card p-5" aria-labelledby="refunds-title">
    <h2 id="refunds-title" className="text-lg font-semibold">Refunds</h2>
    <p className="mt-2 text-sm">Contact support to request a refund review. Eligibility and the approved amount require review. A refund does not itself cancel renewals.</p>
    {query.isError ? <p role="alert" className="mt-3 text-sm">Refund status is unavailable. Contact support.</p>
      : query.data?.length ? <ul className="mt-3 space-y-3">{query.data.map(row => <li key={row.id} className="text-sm">
        <strong>{new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR' }).format(row.amount_minor / 100)}</strong> — {states[row.state]}
      </li>)}</ul> : <p className="mt-3 text-sm">No refund is recorded for your account.</p>}
    <div className="mt-3 flex gap-3"><Button asChild variant="outline"><Link to="/support">Request review</Link></Button>
      <Button variant="outline" disabled={query.isFetching} onClick={() => void query.refetch()}>Refresh status</Button></div>
  </section>
}
