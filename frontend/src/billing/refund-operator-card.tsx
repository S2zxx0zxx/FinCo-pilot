import { useRef, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { useAuth } from '@/contexts/auth-context'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
interface Payment { source_kind: 'activation' | 'renewal'; source_id: string; user_id: string; amount_minor: number; currency: 'INR' }
export function RefundOperatorCard() {
  const { token, user } = useAuth()
  const [selection, setSelection] = useState('')
  const [amount, setAmount] = useState('')
  const [evidence, setEvidence] = useState('')
  const [consent, setConsent] = useState(false)
  const [busy, setBusy] = useState(false)
  const [message, setMessage] = useState('')
  const sending = useRef(false)
  const query = useQuery({ queryKey: ['billing', 'refund-operator', user?.id], enabled: Boolean(token && user?.is_superuser), retry: false,
    queryFn: async (): Promise<Payment[] | null> => {
      const response = await fetch('/api/billing/refunds/operator/payments', { headers: { Authorization: `Bearer ${token}` } })
      if (!response.ok) throw new Error('Sign in again with full authentication to review refunds.')
      const data = await response.json() as { available?: boolean; payments?: Payment[] }
      if (data.available === false) return null
      if (data.available !== true || !Array.isArray(data.payments) || data.payments.some(row => !row || !['activation', 'renewal'].includes(row.source_kind)
          || typeof row.source_id !== 'string' || typeof row.user_id !== 'string' || !Number.isSafeInteger(row.amount_minor) || row.amount_minor < 1 || row.currency !== 'INR')) {
        throw new Error('Payment evidence is unavailable. Reconcile before proceeding.')
      }
      return data.payments
    } })
  if (!token || !user?.is_superuser || query.isPending || query.data === null) return null
  const payment = query.data?.find(row => `${row.source_kind}:${row.source_id}` === selection)
  const valid = payment && /^\d+$/.test(amount) && Number.isSafeInteger(Number(amount)) && Number(amount) >= 100
    && Number(amount) <= payment.amount_minor && /^[a-f0-9]{64}$/.test(evidence) && consent
  async function issue() {
    if (!valid || !payment || sending.current) return
    sending.current = true; setBusy(true); setMessage('')
    try {
      const response = await fetch('/api/billing/refunds/operator', { method: 'POST', headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
        body: JSON.stringify({ source_kind: payment.source_kind, source_id: payment.source_id, amount_minor: Number(amount), evidence_sha256: evidence, authorize: true }) })
      if (!response.ok) throw new Error('Refund could not be verified. Sign in again if needed, then reconcile the same decision before continuing.')
      const row = await response.json() as { state?: string }
      const messages: Record<string, string> = { sending: 'Dispatch recorded; awaiting confirmation.', uncertain: 'Outcome unknown. Reconcile the same decision; do not issue another refund.',
        pending: 'Provider refund is pending.', processed: 'Provider refund is processed. Bank credit timing can vary.', failed: 'Provider refund failed. Review the existing decision with support.' }
      if (!row.state || !Object.hasOwn(messages, row.state)) throw new Error('Refund outcome requires reconciliation.')
      setMessage(messages[row.state])
    } catch { setMessage('Refund could not be verified. Reconcile the existing decision before continuing; sign in again if required.') }
    finally { sending.current = false; setBusy(false) }
  }
  return <section className="rounded-[26px] border bg-card p-5" aria-labelledby="operator-refund-title">
    <h2 id="operator-refund-title" className="text-lg font-semibold">Operator refund review — Test Mode</h2>
    <p className="mt-2 text-sm">This Test Mode action does not return real money. Review actual eligibility evidence and confirm stopping renewals before authorizing a refund. Amounts below are in paise. Repeating an unchanged decision checks its existing outcome.</p>
    {query.isError ? <p role="alert">Sign in again with full authentication to review refunds.</p> : <div className="mt-3 space-y-3">
      <label className="block text-sm">Verified payment<select aria-label="Verified payment" className="mt-1 block w-full rounded-md border bg-background p-2" value={selection} disabled={busy}
        onChange={event => { setSelection(event.target.value); setConsent(false); setMessage('') }}>
        <option value="">Select a payment</option>{query.data?.map(row => <option key={`${row.source_kind}:${row.source_id}`} value={`${row.source_kind}:${row.source_id}`}>
          {row.source_kind} · {row.source_id} · user {row.user_id} · {row.amount_minor} paise</option>)}
      </select></label>
      <label className="block text-sm">Approved amount in paise<Input aria-label="Approved amount in paise" inputMode="numeric" value={amount} disabled={busy} onChange={event => { setAmount(event.target.value); setConsent(false) }} /></label>
      <label className="block text-sm">SHA-256 of reviewed decision evidence<Input aria-label="SHA-256 of reviewed decision evidence" value={evidence} disabled={busy} onChange={event => { setEvidence(event.target.value); setConsent(false) }} /></label>
      <label className="flex gap-2 text-sm"><input type="checkbox" checked={consent} disabled={busy} onChange={event => setConsent(event.target.checked)} />I reviewed the payment, refund eligibility and exact amount, and authorize this refund decision.</label>
      <Button disabled={!valid || busy} onClick={() => void issue()}>{busy ? 'Reconciling…' : 'Authorize or reconcile refund'}</Button>
    </div>}
    {message && <p role="status" className="mt-3 text-sm">{message}</p>}
  </section>
}
