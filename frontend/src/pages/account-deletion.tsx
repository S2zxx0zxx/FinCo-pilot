import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { useAuth } from '@/contexts/auth-context'
import api from '@/lib/api'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'

interface Status {
  id: string
  state: string
  blockers: string[]
  error_code: string | null
  primary_deleted_at: string | null
  completed_at: string | null
  pending_external_count: number
  pending_object_count: number
  tracking_token?: string
}
interface Preview {
  blockers: string[]
  private_workspace_count: number
  preserved_workspace_count: number
  required_operator_steps: number
}
interface OperatorStatus extends Status {
  requirements: string[]
  review_fingerprint: string | null
  receipts: Record<string, unknown>
  user_id: string
}

const copy = {
  en: {
    title: 'Delete personal account', intro: 'Only private personal workspaces are removed. Shared records, payment evidence and an inactive pseudonymous reference may remain. Backups remain pending until their expiry is verified.',
    fresh: 'Sign in again with your full password and second factor, passkey, or OIDC authentication. Submit within five minutes.', login: 'Sign in again', oidc: 'Reauthenticate with OIDC',
    preview: 'Private workspaces / preserved workspaces / required operator checks', request: 'Request deletion', confirmation: 'Type DELETE MY ACCOUNT to confirm', cancel: 'Cancel request',
    saved: 'Save the request ID and secret receipt below before leaving. The secret is shown only once. Do not share it; it allows deletion status lookup after sign-out.',
    copy: 'Copy secret receipt', requests: 'Recent deletion requests',
    receipt: 'Secret receipt', id: 'Request ID', check: 'Check deletion status', status: 'Status', pending: 'External checks / object cleanup pending', blocked: 'Resolve blockers before execution',
    error: 'Request failed. Sign in again if authentication expired; retry without creating duplicate requests.', operator: 'Deletion operator', evidence: 'SHA-256 of real evidence (64 lowercase hex characters)', review: 'Review current inventory', attest: 'Record external evidence', execute: 'Execute or resume deletion',
    backup: 'Record verified backup expiry', cutoff: 'Earliest remaining recoverable-data timestamp (ISO 8601 with timezone)', requirement: 'Exact required check', load: 'Load request',
  },
  hi: {
    title: 'व्यक्तिगत खाता हटाएँ', intro: 'केवल निजी व्यक्तिगत कार्यक्षेत्र हटाए जाएँगे। साझा रिकॉर्ड, भुगतान प्रमाण और निष्क्रिय छद्मनाम वाला संदर्भ रह सकते हैं। बैकअप की समाप्ति सत्यापित होने तक प्रक्रिया लंबित रहेगी।',
    fresh: 'पासवर्ड और दूसरे कारक, पासकी या OIDC से फिर पूरा प्रमाणीकरण करें। पाँच मिनट के भीतर अनुरोध दें।', login: 'फिर साइन इन करें', oidc: 'OIDC से दोबारा प्रमाणीकरण',
    preview: 'निजी कार्यक्षेत्र / सुरक्षित साझा कार्यक्षेत्र / आवश्यक संचालक जाँच', request: 'हटाने का अनुरोध दें', confirmation: 'पुष्टि के लिए DELETE MY ACCOUNT लिखें', cancel: 'अनुरोध रद्द करें',
    saved: 'आगे बढ़ने से पहले अनुरोध पहचान और नीचे दी गई गुप्त रसीद सुरक्षित रखें। रसीद केवल एक बार दिखेगी। इसे साझा न करें; साइन आउट के बाद स्थिति देखने के लिए इसकी जरूरत होगी।',
    copy: 'गुप्त रसीद कॉपी करें', requests: 'हाल के विलोपन अनुरोध',
    receipt: 'गुप्त रसीद', id: 'अनुरोध पहचान', check: 'स्थिति जाँचें', status: 'स्थिति', pending: 'बाहरी जाँच / फ़ाइल सफ़ाई लंबित', blocked: 'कार्रवाई से पहले रुकावटें दूर करें',
    error: 'अनुरोध असफल हुआ। प्रमाणीकरण समाप्त होने पर फिर साइन इन करें। एक ही अनुरोध बार-बार न बनाएँ।', operator: 'हटाने की प्रक्रिया का संचालक', evidence: 'वास्तविक प्रमाण का SHA-256 (64 छोटे अक्षर/अंक)', review: 'वर्तमान डेटा की समीक्षा करें', attest: 'बाहरी प्रमाण दर्ज करें', execute: 'हटाना शुरू करें या फिर चलाएँ',
    backup: 'सत्यापित बैकअप समाप्ति दर्ज करें', cutoff: 'बचे हुए बहाल किए जा सकने वाले डेटा का सबसे पुराना समय (समय क्षेत्र सहित ISO 8601)', requirement: 'ठीक वही आवश्यक जाँच', load: 'अनुरोध खोलें',
  },
}

export default function AccountDeletionPage() {
  const { user } = useAuth()
  const { i18n } = useTranslation()
  const c = i18n.language.startsWith('hi') ? copy.hi : copy.en
  const [preview, setPreview] = useState<Preview | null>(null)
  const [status, setStatus] = useState<Status | null>(null)
  const [id, setId] = useState('')
  const [receipt, setReceipt] = useState('')
  const [confirmation, setConfirmation] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState(false)
  const [operator, setOperator] = useState<OperatorStatus | null>(null)
  const [evidence, setEvidence] = useState('')
  const [requirement, setRequirement] = useState('')
  const [cutoff, setCutoff] = useState('')
  const [oidcEnabled, setOidcEnabled] = useState(false)
  const [requests, setRequests] = useState<Status[]>([])

  useEffect(() => {
    let live = true
    if (user) {
      if (user.is_superuser) api.get<Status[]>('/account-deletion/operator/requests').then(r => { if (live) setRequests(r.data) }).catch(() => { if (live) setError(true) })
      api.get<{ enabled: boolean }>('/auth/oidc/config').then(r => { if (live) setOidcEnabled(r.data.enabled === true) }).catch(() => {})
      Promise.all([api.get<Preview>('/account-deletion/preview'), api.get<Status | null>('/account-deletion/mine')])
        .then(([p, s]) => { if (live) { setPreview(p.data); setStatus(s.data); if (s.data) setId(s.data.id) } })
        .catch(() => { if (live) setError(true) })
    }
    return () => { live = false }
  }, [user])

  async function run(action: () => Promise<void>) {
    setBusy(true); setError(false)
    try { await action() } catch { setError(true) } finally { setBusy(false) }
  }
  async function check() {
    // No application JWT, workspace selector, cookie or URL secret is sent.
    const response = await fetch(`/api/account-deletion/${encodeURIComponent(id)}/status`, {
      headers: { 'X-Deletion-Receipt': receipt }, credentials: 'omit', cache: 'no-store', redirect: 'error',
    })
    if (!response.ok) throw new Error('Status unavailable')
    setStatus(await response.json() as Status)
  }
  async function loadOperator() {
    const response = await api.get<OperatorStatus>(`/account-deletion/operator/${encodeURIComponent(id)}`)
    setOperator(response.data); setStatus(response.data)
  }
  async function operate(action: string, body?: object) {
    await api.post(`/account-deletion/operator/${encodeURIComponent(id)}/${action}`, body)
    await loadOperator()
  }
  const validEvidence = /^[0-9a-f]{64}$/.test(evidence)
  return <main className="mx-auto max-w-3xl space-y-6 p-6">
    <h1 className="text-2xl font-semibold">{c.title}</h1>
    <p>{c.intro}</p>
    <p>{c.fresh}</p>
    <div className="flex gap-4"><Link className="underline" to="/login">{c.login}</Link>{oidcEnabled && <a className="underline" href="/api/auth/oidc/login?reauthenticate=true">{c.oidc}</a>}</div>
    {preview && <section className="space-y-2 rounded border p-4">
      <p>{c.preview}: {preview.private_workspace_count} / {preview.preserved_workspace_count} / {preview.required_operator_steps}</p>
      {!!preview.blockers.length && <p>{c.blocked}: {preview.blockers.join(', ')}</p>}
    </section>}
    {user && (!status || status.state === 'cancelled') && <section className="space-y-3">
      <label htmlFor="deletion-confirmation">{c.confirmation}</label>
      <Input id="deletion-confirmation" value={confirmation} onChange={e => setConfirmation(e.target.value)} autoComplete="off" />
      <Button disabled={busy || confirmation !== 'DELETE MY ACCOUNT'} onClick={() => void run(async () => {
        const response = await api.post<Status>('/account-deletion', { confirmation })
        setStatus(response.data); setId(response.data.id); setReceipt(response.data.tracking_token ?? '')
        setConfirmation('')
      })}>{c.request}</Button>
    </section>}
    {status?.tracking_token && <p className="rounded border p-4">{c.saved}</p>}
    <section className="space-y-3 rounded border p-4">
      <label htmlFor="deletion-id">{c.id}</label><Input id="deletion-id" value={id} onChange={e => setId(e.target.value)} autoComplete="off" />
      <label htmlFor="deletion-receipt">{c.receipt}</label><Input id="deletion-receipt" type="password" value={receipt} onChange={e => setReceipt(e.target.value)} autoComplete="off" />
      <Button disabled={busy || !id || !receipt} variant="outline" onClick={() => void run(() => navigator.clipboard.writeText(JSON.stringify({ id, tracking_token: receipt })))}>{c.copy}</Button>
      <Button disabled={busy || !id || !receipt} onClick={() => void run(check)}>{c.check}</Button>
      {status && <div role="status" className="space-y-2">
        <p>{c.status}: {status.state}</p><p>{c.pending}: {status.pending_external_count} / {status.pending_object_count}</p>
        {!!status.blockers.length && <p>{c.blocked}: {status.blockers.join(', ')}</p>}
        {user && (!operator || operator.id !== status.id || operator.user_id === user.id) && ['requested', 'ready', 'blocked'].includes(status.state) && <Button disabled={busy} variant="outline" onClick={() => void run(async () => {
          const response = await api.post<Status>(`/account-deletion/${encodeURIComponent(status.id)}/cancel`)
          setStatus(response.data)
        })}>{c.cancel}</Button>}
      </div>}
    </section>
    {user?.is_superuser && <section className="space-y-3 rounded border p-4">
      <h2 className="text-xl">{c.operator}</h2>
      <label htmlFor="operator-deletion-requests">{c.requests}</label>
      <select id="operator-deletion-requests" className="w-full rounded border p-2" value={id} onChange={e => setId(e.target.value)}>
        <option value="">—</option>{requests.map(r => <option key={r.id} value={r.id}>{r.id} — {r.state}</option>)}
      </select>
      <Button disabled={busy || !id} onClick={() => void run(loadOperator)}>{c.load}</Button>
      {operator && <>
        <label htmlFor="deletion-evidence">{c.evidence}</label><Input id="deletion-evidence" value={evidence} onChange={e => setEvidence(e.target.value)} autoComplete="off" />
        <Button disabled={busy || !validEvidence} onClick={() => void run(() => operate('review', { evidence_sha256: evidence }))}>{c.review}</Button>
        <label htmlFor="deletion-requirement">{c.requirement}</label>
        <select id="deletion-requirement" className="w-full rounded border p-2" value={requirement} onChange={e => setRequirement(e.target.value)}>
          <option value="">—</option>{operator.requirements.map(r => <option key={r} value={r}>{r}{operator.receipts[r] ? ' ✓' : ''}</option>)}
        </select>
        <Button disabled={busy || !validEvidence || !requirement} onClick={() => void run(() => operate('receipt', { requirement, evidence_sha256: evidence }))}>{c.attest}</Button>
        <Button disabled={busy || !['ready', 'external_retry', 'executing'].includes(operator.state)} onClick={() => void run(() => operate('execute'))}>{c.execute}</Button>
        <label htmlFor="deletion-cutoff">{c.cutoff}</label><Input id="deletion-cutoff" value={cutoff} onChange={e => setCutoff(e.target.value)} />
        <Button disabled={busy || !validEvidence || !cutoff || operator.state !== 'backup_expiry_pending'} onClick={() => void run(() => operate('backup-proof', { evidence_sha256: evidence, verified_after: cutoff }))}>{c.backup}</Button>
      </>}
    </section>}
    {error && <p role="alert">{c.error}</p>}
  </main>
}
