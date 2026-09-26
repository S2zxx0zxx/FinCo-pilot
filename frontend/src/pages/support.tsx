import { useMemo, useState } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { useTranslation } from 'react-i18next'
import type { AxiosError } from 'axios'
import { ArrowLeft, CheckCircle2, ExternalLink, LifeBuoy, Mail, Send, ShieldAlert } from 'lucide-react'
import { support as supportApi, type SupportCategory, type SupportTicketResult } from '@/lib/api'
import { APP_VERSION } from '@/lib/build-info'
import { lastRequestId, normalizeRequestReference, normalizeSupportReference, sanitizeSupportPath } from '@/lib/support'
import { useAuth } from '@/contexts/auth-context'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Card, CardContent } from '@/components/ui/card'
import { FinCoLogo } from '@/components/finco-logo'

const FALLBACK_CATEGORIES: SupportCategory[] = [
  'account_access', 'billing_payment', 'bank_connection', 'transactions_import',
  'safe_to_spend', 'finco_copilot', 'bug_performance', 'privacy_data',
  'feature_request', 'other',
]

function categoryFromQuery(value: string | null): SupportCategory {
  return FALLBACK_CATEGORIES.includes(value as SupportCategory) ? value as SupportCategory : 'other'
}

function providerError(error: unknown): { message: string | null; reference: string | null } {
  const detail = (error as AxiosError<{ detail?: string | { message?: string; reference?: string } }>)?.response?.data?.detail
  if (typeof detail === 'string') return { message: detail, reference: null }
  if (detail && typeof detail === 'object') {
    return {
      message: typeof detail.message === 'string' ? detail.message : null,
      reference: normalizeSupportReference(detail.reference),
    }
  }
  return { message: null, reference: null }
}

export default function SupportPage() {
  const { t, i18n } = useTranslation()
  const navigate = useNavigate()
  const [params] = useSearchParams()
  const { user, token } = useAuth()
  const infoQuery = useQuery({
    queryKey: ['support', 'info'],
    queryFn: () => supportApi.info(),
    staleTime: 1000 * 60 * 10,
    retry: 1,
  })

  const from = sanitizeSupportPath(params.get('from'))
  const diagnosticReference = normalizeRequestReference(params.get('ref')) ?? lastRequestId()
  const [category, setCategory] = useState<SupportCategory>(() => categoryFromQuery(params.get('category')))
  const [subject, setSubject] = useState('')
  const [message, setMessage] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [result, setResult] = useState<SupportTicketResult | null>(null)
  const [submitError, setSubmitError] = useState<{ message: string; reference: string | null } | null>(null)
  const info = infoQuery.data
  const categories = useMemo(() => {
    const allowed = info?.categories?.filter((value): value is SupportCategory =>
      FALLBACK_CATEGORIES.includes(value as SupportCategory),
    )
    return allowed?.length ? allowed : FALLBACK_CATEGORIES
  }, [info?.categories])

  async function submit(event: React.FormEvent) {
    event.preventDefault()
    if (!token || !info?.direct_ticket_submission) return
    setSubmitting(true)
    setSubmitError(null)
    try {
      const created = await supportApi.createTicket({
        category,
        subject,
        message,
        page_path: from,
        app_version: APP_VERSION,
        locale: i18n.resolvedLanguage ?? i18n.language,
        error_reference: diagnosticReference,
      })
      setResult(created)
      setSubject('')
      setMessage('')
    } catch (error) {
      const provider = providerError(error)
      setSubmitError({
        message: provider.message ?? t('support.submitFailed'),
        reference: provider.reference,
      })
    } finally {
      setSubmitting(false)
    }
  }

  return <main className="min-h-screen bg-background px-4 py-6 text-foreground sm:px-6">
    <div className="mx-auto w-full max-w-4xl space-y-6">
      <header className="flex items-start gap-3">
        <Button type="button" variant="outline" size="icon" onClick={() => from ? navigate(from) : navigate(-1)} aria-label={t('support.back')}>
          <ArrowLeft size={16} />
        </Button>
        <div className="flex-1">
          <div className="flex items-center gap-2"><FinCoLogo size={24} className="text-primary" /><h1 className="text-2xl font-semibold tracking-tight">{t('support.title')}</h1></div>
          <p className="mt-1 text-sm text-muted-foreground">{t('support.subtitle')}</p>
        </div>
      </header>

      {!infoQuery.isLoading && !info?.enabled && <Card><CardContent className="space-y-2 p-5">
        <div className="flex items-center gap-2 font-medium"><LifeBuoy size={17} />{t('support.notConfigured')}</div>
        <p className="text-sm text-muted-foreground">{t('support.notConfiguredHint')}</p>
      </CardContent></Card>}

      <div className="grid gap-4 md:grid-cols-3">
        {info?.email && <Card><CardContent className="space-y-3 p-5"><Mail size={19} /><div><div className="font-medium">{t('support.emailTitle')}</div><div className="mt-1 break-all text-xs text-muted-foreground">{info.email}</div></div><a className="text-sm font-medium text-primary hover:underline" href={`mailto:${info.email}`}>{t('support.email')}</a></CardContent></Card>}
        {info?.portal_url && <Card><CardContent className="space-y-3 p-5"><LifeBuoy size={19} /><div className="font-medium">{t('support.portalTitle')}</div><a className="inline-flex items-center gap-1 text-sm font-medium text-primary hover:underline" href={info.portal_url} target="_blank" rel="noreferrer">{t('support.open')} <ExternalLink size={13} /></a></CardContent></Card>}
        {info?.help_center_url && <Card><CardContent className="space-y-3 p-5"><LifeBuoy size={19} /><div className="font-medium">{t('support.helpCenterTitle')}</div><a className="inline-flex items-center gap-1 text-sm font-medium text-primary hover:underline" href={info.help_center_url} target="_blank" rel="noreferrer">{t('support.open')} <ExternalLink size={13} /></a></CardContent></Card>}
      </div>

      {result ? <Card><CardContent className="space-y-4 p-6" role="status">
        <div className="flex items-center gap-2 text-emerald-600"><CheckCircle2 size={20} /><h2 className="font-semibold">{t('support.created')}</h2></div>
        <p className="text-sm text-muted-foreground">{t('support.createdDescription')}</p>
        <dl className="grid gap-3 rounded-lg bg-muted/50 p-4 text-sm sm:grid-cols-2">
          <div><dt className="text-muted-foreground">{t('support.reference')}</dt><dd className="font-mono font-medium">{result.reference}</dd></div>
          {result.ticket_number && <div><dt className="text-muted-foreground">{t('support.ticketNumber')}</dt><dd className="font-mono font-medium">{result.ticket_number}</dd></div>}
        </dl>
        <Button type="button" variant="outline" onClick={() => setResult(null)}>{t('support.contact')}</Button>
      </CardContent></Card> : token && info?.direct_ticket_submission ? <Card><CardContent className="p-6">
        <div className="mb-5"><h2 className="text-lg font-semibold">{t('support.directTitle')}</h2><p className="mt-1 text-sm text-muted-foreground">{t('support.directDescription')}</p></div>
        <form onSubmit={submit} className="space-y-4">
          <div className="space-y-2"><Label htmlFor="support-category">{t('support.category')}</Label><select id="support-category" value={category} onChange={(e) => setCategory(e.target.value as SupportCategory)} className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm">{categories.map(value => <option key={value} value={value}>{t(`support.categories.${value}`)}</option>)}</select></div>
          <div className="space-y-2"><Label htmlFor="support-subject">{t('support.subject')}</Label><Input id="support-subject" value={subject} onChange={(e) => setSubject(e.target.value)} minLength={4} maxLength={160} placeholder={t('support.subjectPlaceholder')} required /></div>
          <div className="space-y-2"><Label htmlFor="support-message">{t('support.message')}</Label><textarea id="support-message" value={message} onChange={(e) => setMessage(e.target.value)} minLength={10} maxLength={5000} placeholder={t('support.messagePlaceholder')} required rows={7} className="flex w-full resize-y rounded-md border border-input bg-background px-3 py-2 text-sm outline-none ring-offset-background placeholder:text-muted-foreground focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2" /></div>
          <div className="rounded-lg border border-amber-500/30 bg-amber-500/5 p-3 text-sm"><div className="flex gap-2"><ShieldAlert className="mt-0.5 shrink-0 text-amber-600" size={17} /><span>{t('support.safeWarning')}</span></div></div>
          {diagnosticReference && <p className="text-xs text-muted-foreground">{t('support.requestReference')}: <span className="font-mono">{diagnosticReference}</span></p>}
          <p className="text-xs text-muted-foreground">{t('support.planPriorityNote')}</p>
          {submitError && <div role="alert" className="rounded-lg bg-destructive/10 p-3 text-sm text-destructive"><p>{submitError.message}</p>{submitError.reference && <p className="mt-1 font-mono">{t('support.reference')}: {submitError.reference}</p>}</div>}
          <Button type="submit" disabled={submitting || subject.trim().length < 4 || message.trim().length < 10}><Send size={15} />{submitting ? t('support.sending') : t('support.send')}</Button>
        </form>
      </CardContent></Card> : info?.enabled && <Card><CardContent className="space-y-3 p-5">
        <p className="text-sm text-muted-foreground">{token ? t('support.submissionUnavailable') : t('support.signInPrompt')}</p>
        {!user && <Button asChild variant="outline"><Link to={`/login?next=${encodeURIComponent('/support')}`}>{t('support.signIn')}</Link></Button>}
      </CardContent></Card>}

      {info?.security_url && <Card><CardContent className="flex flex-col gap-4 p-5 sm:flex-row sm:items-center">
        <ShieldAlert className="shrink-0 text-amber-600" size={22} /><div className="flex-1"><h2 className="font-medium">{t('support.securityTitle')}</h2><p className="mt-1 text-sm text-muted-foreground">{t('support.securityDescription')}</p></div>
        <a className="inline-flex items-center gap-1 text-sm font-medium text-primary hover:underline" href={info.security_url} target="_blank" rel="noreferrer">{t('support.securityAction')} <ExternalLink size={13} /></a>
      </CardContent></Card>}
    </div>
  </main>
}
