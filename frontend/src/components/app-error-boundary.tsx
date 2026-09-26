import { Component, type ReactNode } from 'react'
import { buildSupportUrl } from '@/lib/support'

export class AppErrorBoundary extends Component<{ children: ReactNode }, { failed: boolean }> {
  state = { failed: false }
  static getDerivedStateFromError() { return { failed: true } }
  render() {
    if (!this.state.failed) return this.props.children
    const from = typeof window !== 'undefined' ? window.location.pathname : '/'
    return <main className="min-h-screen flex items-center justify-center p-6"><section className="max-w-md space-y-4" role="alert">
      <h1 className="text-xl font-semibold">We could not display this page</h1>
      <p>Reload to get the current version. If you were saving a change, check your records before submitting it again.</p>
      <div className="flex flex-wrap gap-4">
        <button className="rounded border p-3" onClick={() => window.location.reload()}>Reload page</button>
        <a className="rounded border p-3 underline" href="/">Return home</a>
        <a className="rounded border p-3 underline" href={buildSupportUrl({ from, category: 'bug_performance' })}>Contact support</a>
      </div>
    </section></main>
  }
}
