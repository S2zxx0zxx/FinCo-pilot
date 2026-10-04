import axios, { AxiosError, type AxiosInstance } from 'axios'
import { beforeAll, beforeEach, describe, expect, it, vi } from 'vitest'

let api: AxiosInstance
beforeAll(async () => {
  const create = vi.spyOn(axios, 'create')
  await import('./api')
  api = create.mock.results[0].value as AxiosInstance
  create.mockRestore()
})
beforeEach(() => localStorage.clear())

describe('session request identity', () => {
  it('attaches the current session to ordinary requests', async () => {
    localStorage.setItem('token', 'current')
    const result = await api.get('/synthetic', { adapter: async (config) => ({ data: config.headers.Authorization, status: 200, statusText: 'OK', headers: {}, config }) })
    expect(result.data).toBe('Bearer current')
  })

  it('preserves an explicit departing token despite a replacement login', async () => {
    localStorage.setItem('token', 'replacement')
    const result = await api.post('/auth/logout', {}, { headers: { Authorization: 'Bearer departing' }, adapter: async (config) => ({ data: config.headers.Authorization, status: 200, statusText: 'OK', headers: {}, config }) })
    expect(result.data).toBe('Bearer departing')
  })

  it('does not invalidate replacement login after an old request returns 401', async () => {
    localStorage.setItem('token', 'departing')
    const failure = api.get('/synthetic', { adapter: async (config) => {
      localStorage.setItem('token', 'replacement')
      throw new AxiosError('Rejected', 'ERR_BAD_REQUEST', config, undefined, { data: {}, status: 401, statusText: 'Unauthorized', headers: {}, config })
    } })
    await expect(failure).rejects.toThrow('Rejected')
    expect(localStorage.getItem('token')).toBe('replacement')
  })
})
