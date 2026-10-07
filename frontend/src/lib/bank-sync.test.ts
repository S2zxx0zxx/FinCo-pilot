import { afterEach, beforeEach, expect, it, vi } from 'vitest'
import { connections } from './api'
import { syncBankConnection } from './bank-sync'

vi.mock('./api', () => ({ connections: { sync: vi.fn(), list: vi.fn() } }))

beforeEach(() => {
  vi.useFakeTimers()
  vi.mocked(connections.sync).mockResolvedValue({ connection_id: 'own', task_id: 'task', status: 'queued' })
})
afterEach(() => { vi.useRealTimers(); vi.resetAllMocks() })

it('waits through queue and worker execution instead of treating dispatch as imported data', async () => {
  vi.mocked(connections.list)
    .mockResolvedValueOnce([{ id: 'own', last_sync_status: 'queued' }] as never)
    .mockResolvedValueOnce([{ id: 'own', last_sync_status: 'running' }] as never)
    .mockResolvedValueOnce([{ id: 'own', last_sync_status: 'success' }] as never)
  const result = syncBankConnection('own', { pollMs: 10 })
  await vi.runAllTimersAsync()
  expect((await result).last_sync_status).toBe('success')
  expect(connections.sync).toHaveBeenCalledTimes(1)
  expect(connections.list).toHaveBeenCalledTimes(3)
})

it('preserves the cached outcome rather than claiming a confirmed bank refresh', async () => {
  vi.mocked(connections.list).mockResolvedValue([{ id: 'own', last_sync_status: 'cached' }] as never)
  expect((await syncBankConnection('own')).last_sync_status).toBe('cached')
})

it.each(['action_required', 'rate_limited', 'error'])('surfaces %s without automatically dispatching another refresh', async status => {
  vi.mocked(connections.list).mockResolvedValue([{ id: 'own', last_sync_status: status }] as never)
  await expect(syncBankConnection('own')).rejects.toThrow(status)
  expect(connections.sync).toHaveBeenCalledTimes(1)
})

it('does not accept a different workspace connection as the requested result', async () => {
  vi.mocked(connections.list).mockResolvedValue([{ id: 'foreign', last_sync_status: 'success' }] as never)
  await expect(syncBankConnection('own')).rejects.toThrow('no longer exists')
})

it('reports a slow worker as still running without retrying the provider', async () => {
  vi.mocked(connections.list).mockResolvedValue([{ id: 'own', last_sync_status: 'running' }] as never)
  const result = expect(syncBankConnection('own', { pollMs: 10, timeoutMs: 20 })).rejects.toThrow('still running')
  await vi.runAllTimersAsync()
  await result
  expect(connections.sync).toHaveBeenCalledTimes(1)
})
