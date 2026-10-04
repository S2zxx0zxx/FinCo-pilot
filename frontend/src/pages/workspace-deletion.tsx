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
  objects: Array<{ kind: string; key: string; provider: string; done: boolean }>
  private_workspaces: string[]
}

const copy = {
  en: {
    members: 'Resolve collaborators explicitly before deletion', memberConfirm: 'Confirm member UUID to change or remove', remove: 'Remove member', promote: 'Make owner', demote: 'Make editor', workspace: 'Workspace', detach: 'Detach external manager', resolve: 'Confirm workspace UUID for governance action', archive: 'Archive workspace first', repair: 'Repair unresolved billing ownership (operator evidence required)', transfer: 'Transfer billing to requesting owner (current payer only)', title: 'Delete archived workspace', intro: 'Delete only the selected archived workspace after all collaborators, external management, billing ownership and holds are resolved. Your user account, global subscription and other workspaces remain. Backups remain pending until actual expiry is verified.',
    fresh: 'Sign in again with your full password and second factor, passkey, or OIDC authentication. Submit within five minutes.', login: 'Sign in again', oidc: 'Reauthenticate with OIDC',
    preview: 'Private workspaces / preserved workspaces / required operator checks', request: 'Request deletion', confirmation: 'Type DELETE THIS WORKSPACE to confirm', cancel: 'Cancel request',
    saved: 'Save the request ID and secret receipt below before leaving. The secret is shown only once. Do not share it; it allows deletion status lookup after sign-out.',
    inventory: 'Protected cleanup inventory (operator only)',
    copy: 'Copy secret receipt', requests: 'Recent deletion requests',
    receipt: 'Secret receipt', id: 'Request ID', check: 'Check deletion status', status: 'Status', pending: 'External checks / object cleanup pending', blocked: 'Resolve blockers before execution',
    error: 'Request failed. Sign in again if authentication expired; retry without creating duplicate requests.', operator: 'Deletion operator', evidence: 'SHA-256 of real evidence (64 lowercase hex characters)', review: 'Review current inventory', attest: 'Record external evidence', execute: 'Execute or resume deletion',
    backup: 'Record verified backup expiry', cutoff: 'Earliest remaining recoverable-data timestamp (ISO 8601 with timezone)', requirement: 'Exact required check', load: 'Load request',
  },
  hi: {
    members: 'हटाने से पहले सहयोगियों का स्पष्ट समाधान करें', memberConfirm: 'बदलने या हटाने के लिए सदस्य UUID की पुष्टि', remove: 'सदस्य हटाएँ', promote: 'स्वामी बनाएँ', demote: 'संपादक बनाएँ', workspace: 'कार्यक्षेत्र', detach: 'बाहरी प्रबंधक अलग करें', resolve: 'कार्रवाई की पुष्टि के लिए कार्यक्षेत्र UUID', archive: 'पहले कार्यक्षेत्र संग्रहीत करें', repair: 'अस्पष्ट भुगतान स्वामित्व सुधारें (संचालक प्रमाण आवश्यक)', transfer: 'अनुरोधकर्ता को भुगतान स्वामित्व दें (केवल वर्तमान भुगतानकर्ता)', title: 'संग्रहीत कार्यक्षेत्र हटाएँ', intro: 'केवल चुना हुआ संग्रहीत कार्यक्षेत्र हटेगा। पहले सहयोगियों, बाहरी प्रबंधक, भुगतान स्वामित्व और रोक का समाधान करें। आपका खाता, वैश्विक सदस्यता और अन्य कार्यक्षेत्र सुरक्षित रहेंगे। बैकअप समाप्ति के वास्तविक प्रमाण तक प्रक्रिया लंबित रहेगी।',
    fresh: 'पासवर्ड और दूसरे कारक, पासकी या OIDC से फिर पूरा प्रमाणीकरण करें। पाँच मिनट के भीतर अनुरोध दें।', login: 'फिर साइन इन करें', oidc: 'OIDC से दोबारा प्रमाणीकरण',
    preview: 'निजी कार्यक्षेत्र / सुरक्षित साझा कार्यक्षेत्र / आवश्यक संचालक जाँच', request: 'हटाने का अनुरोध दें', confirmation: 'पुष्टि के लिए DELETE THIS WORKSPACE लिखें', cancel: 'अनुरोध रद्द करें',
    saved: 'आगे बढ़ने से पहले अनुरोध पहचान और नीचे दी गई गुप्त रसीद सुरक्षित रखें। रसीद केवल एक बार दिखेगी। इसे साझा न करें; साइन आउट के बाद स्थिति देखने के लिए इसकी जरूरत होगी।',
    inventory: 'सुरक्षित सफ़ाई सूची (केवल संचालक)',
    copy: 'गुप्त रसीद कॉपी करें', requests: 'हाल के विलोपन अनुरोध',
    receipt: 'गुप्त रसीद', id: 'अनुरोध पहचान', check: 'स्थिति जाँचें', status: 'स्थिति', pending: 'बाहरी जाँच / फ़ाइल सफ़ाई लंबित', blocked: 'कार्रवाई से पहले रुकावटें दूर करें',
    error: 'अनुरोध असफल हुआ। प्रमाणीकरण समाप्त होने पर फिर साइन इन करें। एक ही अनुरोध बार-बार न बनाएँ।', operator: 'हटाने की प्रक्रिया का संचालक', evidence: 'वास्तविक प्रमाण का SHA-256 (64 छोटे अक्षर/अंक)', review: 'वर्तमान डेटा की समीक्षा करें', attest: 'बाहरी प्रमाण दर्ज करें', execute: 'हटाना शुरू करें या फिर चलाएँ',
    backup: 'सत्यापित बैकअप समाप्ति दर्ज करें', cutoff: 'बचे हुए बहाल किए जा सकने वाले डेटा का सबसे पुराना समय (समय क्षेत्र सहित ISO 8601)', requirement: 'ठीक वही आवश्यक जाँच', load: 'अनुरोध खोलें',
  },
}

export default function WorkspaceDeletionPage() {
  const { user } = useAuth()
  const { i18n } = useTranslation()
  const c = i18n.language.startsWith('hi') ? copy.hi : copy.en
  const [workspaces, setWorkspaces] = useState<Array<{ id: string; name: string; role: string; is_archived: boolean }>>([])
  const [workspaceId, setWorkspaceId] = useState('')
  const [members, setMembers] = useState<Array<{ user_id: string; email: string; role: string }>>([])
  const [memberConfirmation, setMemberConfirmation] = useState('')
  const [governanceConfirmation, setGovernanceConfirmation] = useState('')
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
      if (user.is_superuser) api.get<Status[]>('/workspace-deletion/operator/requests').then(r => { if (live) setRequests(r.data) }).catch(() => { if (live) setError(true) })
      api.get<{ enabled: boolean }>('/auth/oidc/config').then(r => { if (live) setOidcEnabled(r.data.enabled === true) }).catch(() => {})
      api.get<typeof workspaces>('/workspace-deletion/workspaces').then(r => { if (live) setWorkspaces(r.data) })
        .catch(() => { if (live) setError(true) })
    }
    return () => { live = false }
  }, [user])

  useEffect(() => {
    let live = true
    setPreview(null); setStatus(null); setOperator(null); setId(''); setReceipt(''); setConfirmation(''); setMembers([]); setMemberConfirmation('')
    if (user && workspaceId) Promise.all([
      api.get<Preview>(`/workspace-deletion/preview/${encodeURIComponent(workspaceId)}`),
      api.get<Status | null>(`/workspace-deletion/mine?workspace_id=${encodeURIComponent(workspaceId)}`),
      api.get<typeof members>(`/workspaces/${encodeURIComponent(workspaceId)}/members`),
    ]).then(([p, s, m]) => { if (live) { setPreview(p.data); setMembers(m.data); setStatus(s.data); if (s.data) setId(s.data.id) } }).catch(() => { if (live) setError(true) })
    return () => { live = false }
  }, [user, workspaceId])

  async function run(action: () => Promise<void>) {
    setBusy(true); setError(false)
    try { await action() } catch { setError(true) } finally { setBusy(false) }
  }
  async function check() {
    // No application JWT, workspace selector, cookie or URL secret is sent.
    const response = await fetch(`/api/workspace-deletion/${encodeURIComponent(id)}/status`, {
      headers: { 'X-Deletion-Receipt': receipt }, credentials: 'omit', cache: 'no-store', redirect: 'error',
    })
    if (!response.ok) throw new Error('Status unavailable')
    setStatus(await response.json() as Status)
  }
  async function loadOperator(targetId = id) {
    const response = await api.get<OperatorStatus>(`/workspace-deletion/operator/${encodeURIComponent(targetId)}`)
    setOperator(response.data); setStatus(response.data)
  }
  async function operate(action: string, body?: object) {
    if (!operator) throw new Error('Load the exact request first')
    const targetId = operator.id
    await api.post(`/workspace-deletion/operator/${encodeURIComponent(targetId)}/${action}`, body)
    await loadOperator(targetId)
  }
  const validEvidence = /^[0-9a-f]{64}$/.test(evidence)
  return <main className="mx-auto max-w-3xl space-y-6 p-6">
    <h1 className="text-2xl font-semibold">{c.title}</h1>
    <p>{c.intro}</p>
    <p>{c.fresh}</p>
    <div className="flex gap-4"><Link className="underline" to="/login">{c.login}</Link>{oidcEnabled && <a className="underline" href="/api/auth/oidc/login?reauthenticate=true">{c.oidc}</a>}</div>
    {user && <section className="space-y-3">
      <label htmlFor="workspace-deletion-target">{c.workspace}</label>
      <select id="workspace-deletion-target" className="w-full rounded border p-2" value={workspaceId} onChange={e => setWorkspaceId(e.target.value)} disabled={busy}>
        <option value="">—</option>{workspaces.filter(w => w.role === 'owner').map(w => <option key={w.id} value={w.id}>{w.name} — {w.id}</option>)}
      </select>
      {workspaceId && workspaces.find(w => w.id === workspaceId)?.is_archived === false && <Button disabled={busy} variant="outline" onClick={() => void run(async () => {
        await api.post(`/workspaces/${encodeURIComponent(workspaceId)}/archive`)
        setWorkspaces(previous => previous.map(w => w.id === workspaceId ? { ...w, is_archived: true } : w))
        const p = await api.get<Preview>(`/workspace-deletion/preview/${encodeURIComponent(workspaceId)}`); setPreview(p.data)
      })}>{c.archive}</Button>}
    </section>}
    {user && workspaceId && members.length > 0 && <section className="space-y-3 rounded border p-4">
      <h2 className="text-xl">{c.members}</h2>
      <label htmlFor="deletion-member-confirmation">{c.memberConfirm}</label><Input id="deletion-member-confirmation" value={memberConfirmation} onChange={e => setMemberConfirmation(e.target.value)} />
      {members.map(member => <div key={member.user_id} className="space-y-2 border-b p-2"><p>{member.email} — {member.role} — {member.user_id}</p>
        <Button disabled={busy || memberConfirmation !== member.user_id || member.user_id === user.id} variant="outline" onClick={() => void run(async () => {
          await api.delete(`/workspaces/${encodeURIComponent(workspaceId)}/members/${encodeURIComponent(member.user_id)}`)
          const response = await api.get<typeof members>(`/workspaces/${encodeURIComponent(workspaceId)}/members`); setMembers(response.data)
          const p = await api.get<Preview>(`/workspace-deletion/preview/${encodeURIComponent(workspaceId)}`); setPreview(p.data); setMemberConfirmation('')
        })}>{c.remove}</Button>
        <Button disabled={busy || memberConfirmation !== member.user_id || member.user_id === user.id} variant="outline" onClick={() => void run(async () => {
          await api.patch(`/workspaces/${encodeURIComponent(workspaceId)}/members/${encodeURIComponent(member.user_id)}`, { role: member.role === 'owner' ? 'editor' : 'owner' })
          const response = await api.get<typeof members>(`/workspaces/${encodeURIComponent(workspaceId)}/members`); setMembers(response.data)
          const p = await api.get<Preview>(`/workspace-deletion/preview/${encodeURIComponent(workspaceId)}`); setPreview(p.data); setMemberConfirmation('')
        })}>{member.role === 'owner' ? c.demote : c.promote}</Button>
      </div>)}
    </section>}
    {preview && <section className="space-y-2 rounded border p-4">
      <p>{c.preview}: {preview.private_workspace_count} / {preview.preserved_workspace_count} / {preview.required_operator_steps}</p>
      {!!preview.blockers.length && <p>{c.blocked}: {preview.blockers.join(', ')}</p>}
    </section>}
    {user && workspaceId && (!status || status.state === 'cancelled') && <section className="space-y-3">
      <label htmlFor="deletion-confirmation">{c.confirmation}</label>
      <Input id="deletion-confirmation" value={confirmation} onChange={e => setConfirmation(e.target.value)} autoComplete="off" />
      <Button disabled={busy || !workspaceId || confirmation !== 'DELETE THIS WORKSPACE'} onClick={() => void run(async () => {
        const response = await api.post<Status>('/workspace-deletion', { confirmation, workspace_id: workspaceId })
        setStatus(response.data); setId(response.data.id); setReceipt(response.data.tracking_token ?? '')
        setConfirmation('')
      })}>{c.request}</Button>
    </section>}
    {user && status && !operator && ['ready', 'blocked'].includes(status.state) && <section className="space-y-3 rounded border p-4">
      <label htmlFor="workspace-governance-confirmation">{c.resolve}</label><Input id="workspace-governance-confirmation" value={governanceConfirmation} onChange={e => setGovernanceConfirmation(e.target.value)} />
      <label htmlFor="workspace-governance-evidence">{c.evidence}</label><Input id="workspace-governance-evidence" value={evidence} onChange={e => setEvidence(e.target.value)} />
      {(['detach-manager', 'transfer-billing'] as const).map(action => <Button key={action} disabled={busy || !validEvidence || governanceConfirmation !== workspaceId} variant="outline" onClick={() => void run(async () => {
        await api.post(`/workspace-deletion/${encodeURIComponent(status.id)}/${action}`, { confirmation: workspaceId, evidence_sha256: evidence })
        const p = await api.get<Preview>(`/workspace-deletion/preview/${encodeURIComponent(workspaceId)}`); setPreview(p.data)
      })}>{action === 'detach-manager' ? c.detach : c.transfer}</Button>)}
    </section>}
    {status?.tracking_token && <p className="rounded border p-4">{c.saved}</p>}
    <section className="space-y-3 rounded border p-4">
      <label htmlFor="deletion-id">{c.id}</label><Input id="deletion-id" disabled={busy} value={id} onChange={e => { setId(e.target.value); setOperator(null) }} autoComplete="off" />
      <label htmlFor="deletion-receipt">{c.receipt}</label><Input id="deletion-receipt" type="password" value={receipt} onChange={e => setReceipt(e.target.value)} autoComplete="off" />
      <Button disabled={busy || !id || !receipt} variant="outline" onClick={() => void run(() => navigator.clipboard.writeText(JSON.stringify({ id, tracking_token: receipt })))}>{c.copy}</Button>
      <Button disabled={busy || !id || !receipt} onClick={() => void run(check)}>{c.check}</Button>
      {status && <div role="status" className="space-y-2">
        <p>{c.status}: {status.state}</p><p>{c.pending}: {status.pending_external_count} / {status.pending_object_count}</p>
        {!!status.blockers.length && <p>{c.blocked}: {status.blockers.join(', ')}</p>}
        {user && (!operator || operator.id !== status.id || operator.user_id === user.id) && ['requested', 'ready', 'blocked'].includes(status.state) && <Button disabled={busy} variant="outline" onClick={() => void run(async () => {
          const response = await api.post<Status>(`/workspace-deletion/${encodeURIComponent(status.id)}/cancel`)
          setStatus(response.data)
        })}>{c.cancel}</Button>}
      </div>}
    </section>
    {user?.is_superuser && <section className="space-y-3 rounded border p-4">
      <h2 className="text-xl">{c.operator}</h2>
      <label htmlFor="operator-deletion-requests">{c.requests}</label>
      <select id="operator-deletion-requests" className="w-full rounded border p-2" disabled={busy} value={id} onChange={e => { setId(e.target.value); setOperator(null) }}>
        <option value="">—</option>{requests.map(r => <option key={r.id} value={r.id}>{r.id} — {r.state}</option>)}
      </select>
      <Button disabled={busy || !id} onClick={() => void run(loadOperator)}>{c.load}</Button>
      {operator && <>
        <label htmlFor="deletion-inventory">{c.inventory}</label>
        <textarea id="deletion-inventory" readOnly className="w-full rounded border p-2" rows={6} value={JSON.stringify({ workspaces: operator.private_workspaces, objects: operator.objects }, null, 2)} />
        <label htmlFor="operator-workspace-confirmation">{c.resolve}</label><Input id="operator-workspace-confirmation" value={governanceConfirmation} onChange={e => setGovernanceConfirmation(e.target.value)} />
        <Button disabled={busy || !validEvidence || governanceConfirmation !== operator.private_workspaces[0]} onClick={() => void run(() => operate('repair-billing', { confirmation: governanceConfirmation, evidence_sha256: evidence }))}>{c.repair}</Button>
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
