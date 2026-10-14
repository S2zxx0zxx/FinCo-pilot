export function SessionUnavailableNotice() {
  return (
    <main role="alert" className="flex min-h-screen flex-col items-center justify-center gap-4 p-6 text-center">
      <h1 className="text-xl font-semibold">Unable to verify your session</h1>
      <p className="max-w-md text-sm text-muted-foreground">
        FinCo-Pilot is temporarily unavailable. Your sign-in has not been discarded.
        No account data will be shown until the server can verify your session.
      </p>
      <button
        type="button"
        className="rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground"
        onClick={() => window.location.reload()}
      >
        Retry connection
      </button>
    </main>
  )
}
