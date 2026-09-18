import { connections } from '@/lib/api'
import type { BankConnection } from '@/types'

type SyncStatus =
  | 'idle'
  | 'queued'
  | 'running'
  | 'success'
  | 'cached'
  | 'rate_limited'
  | 'action_required'
  | 'error'

export type SyncAwareConnection = BankConnection & {
  last_sync_started_at?: string | null
  last_provider_refresh_at?: string | null
  last_sync_status?: SyncStatus
  last_sync_error?: string | null
}

const TERMINAL = new Set<SyncStatus>([
  'success',
  'cached',
  'rate_limited',
  'action_required',
  'error',
])

const sleep = (ms: number) => new Promise((resolve) => window.setTimeout(resolve, ms))

/**
 * Dispatch a bank sync and observe the connection row until the worker reaches
 * a terminal state. The HTTP request itself returns immediately (202), so
 * provider refreshes that legitimately take 60–90 seconds cannot be killed by
 * browser/proxy timeouts.
 */
export async function syncBankConnection(
  connectionId: string,
  options: { timeoutMs?: number; pollMs?: number } = {},
): Promise<SyncAwareConnection> {
  const timeoutMs = options.timeoutMs ?? 180_000
  const pollMs = options.pollMs ?? 1_500

  // Runtime response is a dispatch receipt. The legacy API client return type
  // still says BankConnection; we intentionally ignore its shape here and use
  // the canonical connection row as the source of truth.
  await connections.sync(connectionId)

  const deadline = Date.now() + timeoutMs
  let latest: SyncAwareConnection | undefined

  while (Date.now() < deadline) {
    const all = (await connections.list()) as SyncAwareConnection[]
    latest = all.find((connection) => connection.id === connectionId)
    if (!latest) throw new Error('Bank connection no longer exists.')

    const status = latest.last_sync_status ?? 'idle'
    if (TERMINAL.has(status)) {
      if (status === 'success' || status === 'cached') return latest
      throw new Error(latest.last_sync_error || `Bank sync finished with status: ${status}`)
    }

    await sleep(pollMs)
  }

  // The worker may still be healthy and processing a slow institution. Avoid a
  // false "sync failed" claim; the user can leave the screen and the job keeps
  // running server-side.
  throw new Error(
    latest?.last_sync_status === 'running'
      ? 'Bank sync is still running in the background. Refresh this page shortly to see the latest data.'
      : 'Bank sync is queued in the background. Refresh this page shortly to see the latest data.',
  )
}
