import { useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { recoveryApi } from '@/lib/recovery-api'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'

type Mode = 'forgot' | 'reset' | 'verify' | 'request-verification'

export default function AccountRecovery({ mode }: { mode: Mode }) {
  const [params, setParams] = useSearchParams()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [confirmation, setConfirmation] = useState('')
  const [busy, setBusy] = useState(false)
  const [message, setMessage] = useState('')
  const [error, setError] = useState('')
  const [done, setDone] = useState(false)
  const token = params.get('token') || ''
  const needsToken = mode === 'reset' || mode === 'verify'
  const title = { forgot: 'Forgot your password?', reset: 'Set a new password', verify: 'Verify your email', 'request-verification': 'Request verification email' }[mode]

  async function submit(event: React.FormEvent) {
    event.preventDefault()
    setError('')
    if (mode === 'reset' && password !== confirmation) {
      setError('Passwords do not match.')
      return
    }
    setBusy(true)
    try {
      if (mode === 'forgot') await recoveryApi.forgotPassword(email)
      if (mode === 'reset') await recoveryApi.resetPassword(token, password)
      if (mode === 'verify') await recoveryApi.verifyEmail(token)
      if (mode === 'request-verification') await recoveryApi.requestVerification(email)
      setMessage(mode === 'reset' ? 'Password changed. Sign in again on your devices.' : mode === 'verify' ? 'Email verified. You can return to your account.' : 'If this address is eligible, an email will arrive shortly. Check your spam folder too.')
      setDone(true)
      if (needsToken) setParams({}, { replace: true })
      setPassword('')
      setConfirmation('')
    } catch {
      setError(needsToken ? 'This link could not be used. It may have expired or already been used. Request a new email.' : 'We could not process your request. Please try again later.')
    } finally {
      setBusy(false)
    }
  }

  return <main className="min-h-screen flex items-center justify-center bg-background p-5">
    <section className="w-full max-w-md rounded-xl border bg-card p-6 space-y-5">
      <h1 className="text-xl font-semibold">{title}</h1>
      <p className="text-sm text-muted-foreground">Use the email address associated with your FinCo-Pilot account.</p>
      {message && <p role="status">{message}</p>}
      {error && <p role="alert" className="text-destructive">{error}</p>}
      {!done && <form onSubmit={submit} className="space-y-4">
        {!needsToken && <div className="space-y-2"><Label htmlFor="recovery-email">Email</Label><Input id="recovery-email" type="email" autoComplete="email" value={email} onChange={e => setEmail(e.target.value)} required /></div>}
        {mode === 'reset' && <>
          <div className="space-y-2"><Label htmlFor="new-password">New password (8–128 characters)</Label><Input id="new-password" type="password" autoComplete="new-password" minLength={8} maxLength={128} value={password} onChange={e => setPassword(e.target.value)} required /></div>
          <div className="space-y-2"><Label htmlFor="confirm-password">Confirm password</Label><Input id="confirm-password" type="password" autoComplete="new-password" minLength={8} maxLength={128} value={confirmation} onChange={e => setConfirmation(e.target.value)} required /></div>
        </>}
        {needsToken && !token && <p role="alert">Open the complete link from your email, or request a new one below.</p>}
        <Button className="w-full" disabled={busy || (needsToken && !token)}>{busy ? 'Please wait…' : mode === 'reset' ? 'Change password' : mode === 'verify' ? 'Verify email' : 'Send email'}</Button>
      </form>}
      <nav className="flex flex-wrap gap-4 text-sm underline">
        <Link to="/login">Back to sign in</Link>
        {mode === 'reset' && <Link to="/forgot-password">Request a new reset link</Link>}
        {mode === 'verify' && <Link to="/request-verification">Request a new verification link</Link>}
      </nav>
    </section>
  </main>
}
