import { useState } from 'react'
import { useWorkspace } from '@/contexts/workspace-context'
import { useAuth } from '@/contexts/auth-context'
import { dashboard } from '@/lib/api'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'

type Result = Awaited<ReturnType<typeof dashboard.spendingPlan>>

export default function SpendingPlanPage() {
  const { current } = useWorkspace()
  // A workspace switch discards the previous workspace's inputs and result.
  return <SpendingPlanForm key={current?.id} />
}

function SpendingPlanForm() {
  const { user } = useAuth()
  const [days, setDays] = useState('30')
  const [emergency, setEmergency] = useState('0')
  const [goals, setGoals] = useState('0')
  const [other, setOther] = useState('0')
  const [reviewed, setReviewed] = useState(false)
  const [result, setResult] = useState<Result | null>(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const currency = result?.currency || user?.preferences?.currency_display || 'INR'
  const money = (value: string | number) => new Intl.NumberFormat(undefined, { style: 'currency', currency }).format(Number(value))
  async function calculate(event: React.FormEvent) {
    event.preventDefault()
    setBusy(true)
    setError('')
    setResult(null)
    try {
      setResult(await dashboard.spendingPlan({ horizon_days: Number(days), emergency_buffer: emergency, goal_reserve: goals, other_obligations: other, obligations_reviewed: reviewed }))
    } catch {
      setError('The spending plan could not be calculated. Check your connection and try again.')
    } finally {
      setBusy(false)
    }
  }
  return <main className="mx-auto max-w-3xl space-y-6 p-4 md:p-8">
    <header className="space-y-2"><h1 className="text-2xl font-semibold">Safe to spend</h1><p className="text-muted-foreground">Plan from your current workspace’s cash, debts and upcoming expenses. Review all obligations before relying on an estimate.</p></header>
    <form onSubmit={calculate} onChange={() => setResult(null)} className="rounded-xl border p-5 space-y-4">
      <div className="space-y-2"><Label htmlFor="plan-days">Plan for how many days?</Label><Input id="plan-days" type="number" min={1} max={90} required value={days} onChange={e => setDays(e.target.value)} /></div>
      {[['emergency', 'Emergency savings to protect', emergency, setEmergency], ['goals', 'Additional goal contributions', goals, setGoals], ['other', 'Other obligations, including loan repayments not already scheduled', other, setOther]].map(([id, label, value, setter]) => <div key={id as string} className="space-y-2"><Label htmlFor={`plan-${id}`}>{label as string} ({currency})</Label><Input id={`plan-${id}`} type="number" min="0" max="999999999999" step="0.01" required value={value as string} onChange={e => (setter as (value: string) => void)(e.target.value)} /></div>)}
      <label className="flex gap-3 text-sm"><input type="checkbox" checked={reviewed} onChange={e => setReviewed(e.target.checked)} />I checked that my balances, upcoming bills and additional obligations are complete and current.</label>
      <Button disabled={busy}>{busy ? 'Calculating…' : 'Calculate spending plan'}</Button>
    </form>
    {error && <p role="alert" className="text-destructive">{error}</p>}
    {result && <section aria-live="polite" className="space-y-5 rounded-xl border p-5">
      <p className="text-sm">Snapshot: {result.as_of} · Through {result.through}</p>
      {result.safe_to_spend !== null ? <div><h2 className="text-lg">Estimated safe to spend</h2><p className="text-3xl font-semibold">{money(result.safe_to_spend)}</p><p>{money(result.daily_allowance!)} per day</p>{Number(result.shortfall) > 0 && <p role="alert" className="text-destructive">Your plan has a shortfall of {money(result.shortfall!)}. Reduce planned spending or review your obligations.</p>}</div> : <div><h2 className="font-semibold">Review needed before an amount is available</h2><ul className="list-disc pl-5">{result.blockers.map(item => <li key={item}>{item}</li>)}</ul></div>}
      <dl className="space-y-2">{[['Cash balance', result.cash_balance], ['Card debt reserved', result.card_debt_reserve], ['Upcoming outflows reserved', result.upcoming_outflows], ['Emergency buffer', result.emergency_buffer], ['Goal contributions', result.goal_reserve], ['Other obligations', result.other_obligations]].map(([label, value]) => <div key={label} className="flex justify-between gap-4"><dt>{label}</dt><dd>{money(value)}</dd></div>)}</dl>
      <details><summary className="cursor-pointer font-medium">How this estimate works</summary><ul className="mt-3 list-disc space-y-2 pl-5 text-sm text-muted-foreground">{result.assumptions.map(item => <li key={item}>{item}</li>)}</ul></details>
    </section>}
  </main>
}
