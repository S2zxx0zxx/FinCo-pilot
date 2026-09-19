import { Component, type ReactNode } from 'react'

export class AppErrorBoundary extends Component<{ children: ReactNode }, { failed: boolean }> {
  state = { failed: false }
  static getDerivedStateFromError() { return { failed: true } }
  render() {
    if (!this.state.failed) return this.props.children
    return <main className="min-h-screen flex items-center justify-center p-6"><section className="max-w-md space-y-4" role="alert">
      <h1 className="text-xl font-semibold">We could not display this page</h1>
      <p>Reload to get the current version. If you were saving a change, check your records before submitting it again.</p>
      <button className="rounded border p-3" onClick={() => window.location.reload()}>Reload page</button>
      <a className="ml-4 underline" href="/">Return home</a>
    </section></main>
  }
}
