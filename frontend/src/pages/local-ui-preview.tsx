import { useState } from 'react'
import { Link, Navigate } from 'react-router-dom'
import {
  ArrowLeftRight, BarChart3, ChevronRight, CreditCard, LayoutDashboard,
  LockKeyhole, PiggyBank, Settings, ShieldCheck, Target, Wallet,
} from 'lucide-react'
import { FinCoLogo } from '@/components/finco-logo'
import { loginPaused, uiPreviewAvailable } from '@/lib/local-ui-preview'

/**
 * Public-facing UI-only shell while sign-in is temporarily paused.
 * No auth tokens are issued, no actual app route is unlocked, and no API is called.
 */
const screens = [
  { title: 'Overview', icon: LayoutDashboard, description: 'Your financial dashboard at a glance.' },
  { title: 'Transactions', icon: ArrowLeftRight, description: 'A place for your income and expenses.' },
  { title: 'Accounts', icon: CreditCard, description: 'Connect or manage your financial accounts after signing in.' },
  { title: 'Budgets', icon: PiggyBank, description: 'Plan spending by category and period.' },
  { title: 'Goals', icon: Target, description: 'Track progress toward financial goals.' },
  { title: 'Reports', icon: BarChart3, description: 'Review financial trends and reports.' },
  { title: 'Settings', icon: Settings, description: 'Manage preferences and workspace settings.' },
] as const

export default function LocalUiPreviewPage() {
  const [screen, setScreen] = useState<(typeof screens)[number]['title']>('Overview')

  if (!uiPreviewAvailable) return <Navigate to="/login" replace />

  const active = screens.find((item) => item.title === screen) ?? screens[0]

  return (
    <div className="min-h-screen bg-background text-foreground">
      <header className="flex min-h-16 items-center justify-between gap-4 border-b px-5 md:px-8">
        <div className="flex items-center gap-3">
          <div className="rounded-xl bg-primary/10 p-2 text-primary">
            <FinCoLogo size={22} />
          </div>
          <div>
            <div className="font-semibold leading-tight">FinCo-Pilot</div>
            <div className="text-xs text-muted-foreground">{loginPaused ? 'UI Preview · Sign-in paused' : 'Local UI preview'}</div>
          </div>
        </div>
        {!loginPaused && (
          <Link to="/login?auth=real" className="flex items-center gap-2 rounded-lg border px-3 py-2 text-sm hover:bg-muted">
            <LockKeyhole size={15} /> Real sign in
          </Link>
        )}
      </header>

      <div className="border-b bg-muted/40 px-5 py-3 text-sm md:px-8" role="status">
        <div className="flex items-start gap-2">
          <ShieldCheck className="mt-0.5 shrink-0 text-primary" size={17} />
          <span><strong>Preview only.</strong> {loginPaused ? 'Sign-in is temporarily paused. ' : ''}No login or verification was performed. No real users, accounts, or financial records can be accessed here.</span>
        </div>
      </div>

      <div className="flex min-h-[calc(100vh-124px)]">
        <aside className="hidden w-60 shrink-0 border-r p-4 md:block">
          <div className="mb-4 px-3 pt-1 text-xs font-semibold uppercase tracking-widest text-muted-foreground">Workspace</div>
          <nav className="space-y-1" aria-label="Preview navigation">
            {screens.map((item) => {
              const Icon = item.icon
              return (
                <button
                  key={item.title}
                  type="button"
                  onClick={() => setScreen(item.title)}
                  aria-current={screen === item.title ? 'page' : undefined}
                  className={`flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-left text-sm transition-colors ${screen === item.title ? 'bg-primary/10 font-semibold text-primary' : 'text-muted-foreground hover:bg-muted hover:text-foreground'}`}
                >
                  <Icon size={17} />{item.title}
                </button>
              )
            })}
          </nav>
          <div className="mt-10 rounded-xl border bg-muted/30 p-3 text-xs text-muted-foreground">
            This is a visual preview, not an authenticated workspace.
          </div>
        </aside>

        <main className="min-w-0 flex-1 px-5 py-7 md:px-10 md:py-10">
          <nav aria-label="Mobile preview navigation" className="mb-6 flex gap-2 overflow-x-auto pb-2 md:hidden">
            {screens.map((item) => (
              <button key={item.title} type="button" onClick={() => setScreen(item.title)}
                className={`whitespace-nowrap rounded-lg border px-3 py-2 text-sm ${screen === item.title ? 'bg-primary text-primary-foreground' : 'bg-background'}`}>
                {item.title}
              </button>
            ))}
          </nav>

          <div className="mb-7 flex flex-wrap items-start justify-between gap-4">
            <div>
              <div className="mb-2 flex items-center gap-2 text-xs text-muted-foreground">
                Demo workspace <ChevronRight size={13} /> {active.title}
              </div>
              <h1 className="text-2xl font-bold tracking-tight md:text-3xl">{active.title}</h1>
              <p className="mt-2 text-sm text-muted-foreground">{active.description}</p>
            </div>
            <span className="rounded-full border px-3 py-1 text-xs font-medium text-muted-foreground">No data connected</span>
          </div>

          <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
            {[
              { label: 'Total balance', icon: Wallet, value: '—' },
              { label: 'Monthly activity', icon: ArrowLeftRight, value: '—' },
              { label: 'Active accounts', icon: CreditCard, value: '—' },
            ].map((metric) => {
              const Icon = metric.icon
              return (
                <div key={metric.label} className="rounded-xl border bg-card p-5 shadow-sm">
                  <div className="flex items-center justify-between gap-4">
                    <span className="text-sm text-muted-foreground">{metric.label}</span>
                    <Icon className="text-muted-foreground" size={18} />
                  </div>
                  <div className="mt-6 text-3xl font-semibold">{metric.value}</div>
                  <div className="mt-2 text-xs text-muted-foreground">Available after real sign in</div>
                </div>
              )
            })}
          </div>

          <div className="mt-5 grid gap-5 xl:grid-cols-[1.5fr_1fr]">
            <div className="rounded-xl border bg-card p-6 shadow-sm">
              <div className="flex items-center gap-2 font-semibold"><BarChart3 size={18} /> Financial activity</div>
              <p className="mt-1 text-sm text-muted-foreground">No activity is loaded in preview mode.</p>
              <div className="mt-7 flex h-44 items-center justify-center rounded-lg border border-dashed bg-muted/20 text-sm text-muted-foreground">
                Chart area preview
              </div>
            </div>
            <div className="rounded-xl border bg-card p-6 shadow-sm">
              <div className="flex items-center gap-2 font-semibold"><Target size={18} /> Quick access</div>
              <p className="mt-1 text-sm text-muted-foreground">Browse the layout without an account.</p>
              <div className="mt-5 space-y-2">
                {screens.slice(1, 5).map((item) => (
                  <button type="button" key={item.title} onClick={() => setScreen(item.title)}
                    className="flex w-full items-center justify-between rounded-lg border px-3 py-3 text-left text-sm hover:bg-muted">
                    {item.title} <ChevronRight size={16} />
                  </button>
                ))}
              </div>
            </div>
          </div>

          <p className="mt-7 text-center text-xs text-muted-foreground">
            UI preview only • Backend authentication and all financial APIs remain protected.
          </p>
        </main>
      </div>
    </div>
  )
}
