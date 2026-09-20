import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { isAxiosError } from 'axios'
import { loans, type LoanPlan, type LoanPlanInput } from '@/lib/api'
import { useWorkspace } from '@/contexts/workspace-context'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'

function message(error: unknown): string {
  if (isAxiosError(error) && typeof error.response?.data?.detail === 'string') return error.response.data.detail
  return 'Could not save this loan plan. Check your connection, reload the list before retrying, and verify your inputs.'
}

export default function LoansPage() {
  const { current } = useWorkspace()
  if (!current) return <p role="status" className="p-6">Loading workspace…</p>
  return <LoanWorkspace key={current.id} workspaceId={current.id} currency={current.default_currency || 'INR'} />
}

function LoanWorkspace({ workspaceId, currency }: { workspaceId: string; currency: string }) {
  const { canWrite } = useWorkspace()
  const queryClient = useQueryClient()
  const [selected, setSelected] = useState<string | null>(null)
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const empty: LoanPlanInput = { name: '', principal: '', annual_rate: '', term_months: 12, first_due_date: '', currency, paid_installments: 0 }
  const [draft, setDraft] = useState(empty)
  const list = useQuery({ queryKey: ['loans', workspaceId], queryFn: loans.list })
  async function refresh() {
    await queryClient.invalidateQueries({ queryKey: ['loans', workspaceId] })
    await queryClient.invalidateQueries({ queryKey: ['loan-detail', workspaceId] })
  }
  async function create(event: React.FormEvent) {
    event.preventDefault()
    setBusy(true)
    setError('')
    try {
      const result = await loans.create(draft)
      setDraft(empty)
      setSelected(result.id)
      await refresh()
    } catch (error) { setError(message(error)) } finally { setBusy(false) }
  }
  return <main className="mx-auto max-w-5xl space-y-6 p-4 md:p-8">
    <header className="space-y-2">
      <h1 className="text-2xl font-semibold">Loans and EMI plans</h1>
      <p className="text-muted-foreground">Monthly fixed-rate, reducing-balance estimates. Payment counts are entered by you, not verified by your bank. Compare the schedule with your lender’s statement.</p>
      <p className="text-sm">Fees, daily interest, floating rates, partial payments and early principal repayments are not modelled. Add those obligations separately. Saving a plan does not create transactions or move money.</p>
      <Link className="inline-block underline" to="/spending-plan">Open safe-to-spend plan</Link>
    </header>
    {canWrite && <form onSubmit={create} className="space-y-4 rounded-xl border p-5">
      <h2 className="font-semibold">Add a repayment plan</h2>
      <fieldset disabled={busy} className="grid gap-4 sm:grid-cols-2">
        <div><Label htmlFor="loan-name">Loan name</Label><Input id="loan-name" required maxLength={120} value={draft.name} onChange={e => setDraft({ ...draft, name: e.target.value })} /></div>
        <div><Label htmlFor="loan-currency">Currency (three-letter code)</Label><Input id="loan-currency" required pattern="[A-Z]{3}" maxLength={3} value={draft.currency} onChange={e => setDraft({ ...draft, currency: e.target.value.toUpperCase() })} /></div>
        <div><Label htmlFor="loan-principal">Original principal</Label><Input id="loan-principal" type="number" required min={1} max="999999999999" step="0.01" value={draft.principal} onChange={e => setDraft({ ...draft, principal: e.target.value })} /></div>
        <div><Label htmlFor="loan-rate">Annual interest rate (%)</Label><Input id="loan-rate" type="number" required min={0} max={60} step="0.0001" value={draft.annual_rate} onChange={e => setDraft({ ...draft, annual_rate: e.target.value })} /></div>
        <div><Label htmlFor="loan-term">Total monthly installments</Label><Input id="loan-term" type="number" required min={1} max={600} step={1} value={draft.term_months} onChange={e => setDraft({ ...draft, term_months: Number(e.target.value) })} /></div>
        <div><Label htmlFor="loan-first">First installment due date</Label><Input id="loan-first" type="date" required min="2000-01-01" max="2100-12-31" value={draft.first_due_date} onChange={e => setDraft({ ...draft, first_due_date: e.target.value })} /></div>
        <div><Label htmlFor="loan-paid">Consecutive full installments already paid</Label><Input id="loan-paid" type="number" required min={0} max={draft.term_months} step={1} value={draft.paid_installments} onChange={e => setDraft({ ...draft, paid_installments: Number(e.target.value) })} /></div>
      </fieldset>
      <p className="text-sm text-muted-foreground">The first due date anchors each month. Month-end stays month-end. The final installment adjusts for rounding. Contract inputs stay fixed after saving; archive an incorrect plan before replacing it.</p>
      <Button disabled={busy || list.isPending || list.isError}>{busy ? 'Saving…' : 'Save loan plan'}</Button>
    </form>}
    {error && <p role="alert" className="text-destructive">{error}</p>}
    {list.isPending && <p role="status">Loading loan plans…</p>}
    {list.isError && <div role="alert"><p>Loan plans could not be loaded.</p><Button variant="outline" onClick={() => void list.refetch()}>Retry</Button></div>}
    {list.data?.length === 0 && <p>No loan plans in this workspace yet.</p>}
    <div className="flex flex-wrap gap-2">{list.data?.map(loan => <Button key={loan.id} variant={selected === loan.id ? 'default' : 'outline'} onClick={() => setSelected(loan.id)}>{loan.name}{loan.archived ? ' (archived)' : ''}</Button>)}</div>
    {selected && <LoanDetails key={selected} id={selected} workspaceId={workspaceId} onSaved={refresh} />}
  </main>
}

function LoanDetails({ id, workspaceId, onSaved }: { id: string; workspaceId: string; onSaved: () => Promise<void> }) {
  const detail = useQuery({ queryKey: ['loan-detail', workspaceId, id], queryFn: () => loans.get(id) })
  const { canWrite } = useWorkspace()
  if (detail.isPending) return <p role="status">Loading repayment schedule…</p>
  if (detail.isError) return <div role="alert"><p>Schedule could not be loaded.</p><Button variant="outline" onClick={() => void detail.refetch()}>Retry</Button></div>
  const data = detail.data
  const money = (value: string) => new Intl.NumberFormat(undefined, { style: 'currency', currency: data.loan.currency }).format(Number(value))
  return <section className="space-y-4 rounded-xl border p-5">
    <h2 className="text-xl font-semibold">{data.loan.name}</h2>
    <p>Estimated regular installment: {money(data.monthly_payment)} · Total scheduled interest: {money(data.total_interest)}</p>
    <p>Estimated principal remaining after reported payments: {money(data.remaining_principal)}</p>
    <p className="text-sm">Last manual update: {new Date(data.loan.updated_at).toLocaleString()}. Unpaid installments due within your spending horizon, including overdue installments, are reserved in safe-to-spend. An EMI also entered as a recurring or pending expense is conservatively reserved twice. Do not add this plan again under other obligations.</p>
    {canWrite && <PaymentEditor key={data.loan.version} loan={data.loan} onSaved={onSaved} />}
    <div className="overflow-auto max-h-[32rem]">
      <table className="w-full text-sm"><caption className="text-left py-2">Estimated schedule — “reported paid” is your confirmation, not a bank match.</caption>
        <thead><tr>{['#', 'Due date', 'Payment', 'Principal', 'Interest', 'Balance', 'Status'].map(label => <th key={label} scope="col" className="p-2 text-left whitespace-nowrap">{label}</th>)}</tr></thead>
        <tbody>{data.schedule.map(item => <tr key={item.number} className="border-t">
          <td className="p-2">{item.number}</td><td className="p-2 whitespace-nowrap">{item.due_date}</td>
          {[item.payment, item.principal, item.interest, item.remaining_principal].map((value, index) => <td key={index} className="p-2 whitespace-nowrap">{money(value)}</td>)}
          <td className="p-2 whitespace-nowrap">{item.reported_paid ? 'Reported paid' : 'Not reported paid'}</td>
        </tr>)}</tbody>
      </table>
    </div>
  </section>
}

function PaymentEditor({ loan, onSaved }: { loan: LoanPlan; onSaved: () => Promise<void> }) {
  const [paid, setPaid] = useState(String(loan.paid_installments))
  const [archived, setArchived] = useState(loan.archived)
  const [confirmed, setConfirmed] = useState(false)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  async function save(event: React.FormEvent) {
    event.preventDefault()
    if (!confirmed) return
    setBusy(true)
    setError('')
    try {
      await loans.update(loan.id, { version: loan.version, paid_installments: Number(paid), archived })
      await onSaved()
    } catch (error) { setError(message(error)) } finally { setBusy(false) }
  }
  return <form onSubmit={save} className="space-y-3 border-y py-4">
    <Label htmlFor="loan-update-paid">Consecutive full installments paid (from installment 1)</Label>
    <Input id="loan-update-paid" type="number" min={0} max={loan.term_months} step={1} required disabled={busy} value={paid} onChange={e => { setPaid(e.target.value); setConfirmed(false) }} />
    <label className="flex gap-2"><input type="checkbox" checked={archived} disabled={busy} onChange={e => { setArchived(e.target.checked); setConfirmed(false) }} />Archive this plan and remove its reserve from safe-to-spend</label>
    <label className="flex gap-2"><input type="checkbox" checked={confirmed} disabled={busy} onChange={e => setConfirmed(e.target.checked)} />I checked my lender’s statement. Any archived loan’s remaining obligations are covered elsewhere in my spending plan.</label>
    <Button disabled={busy || !confirmed}>{busy ? 'Saving…' : 'Update reported status'}</Button>
    {error && <p role="alert" className="text-destructive">{error}</p>}
  </form>
}
