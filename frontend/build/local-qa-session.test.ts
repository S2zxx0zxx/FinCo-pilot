import { afterEach, describe, expect, it, vi } from 'vitest'
import type { ViteDevServer } from 'vite'
import { localQaSessionPlugin } from './local-qa-session'

const options = {
  mode: 'development',
  enabled: true,
  frontendUrl: 'http://localhost:3300',
  backendUrl: 'http://backend:8000',
  email: 'qa-owner@example.com',
  password: 'long-private-qa-password-more-than-24',
}

function createMiddleware(config = options) {
  const middleware = vi.fn()
  const server = {
    middlewares: {
      use: middleware,
    },
  } as unknown as ViteDevServer
  const hook = localQaSessionPlugin(config).configureServer
  if (typeof hook !== 'function') throw new Error('QA middleware hook missing')
  void hook(server)
  return middleware
}

function invoke(handler: (...args: unknown[]) => void, overrides?: {
  method?: string
  host?: string
  origin?: string
  fetchSite?: string
  qaHeader?: string
}) {
  const res = {
    statusCode: 200,
    setHeader: vi.fn(),
    end: vi.fn(),
  }
  const next = vi.fn()
  handler({
    url: '/__qa/session',
    method: overrides?.method ?? 'POST',
    headers: {
      host: overrides?.host ?? 'localhost:3300',
      origin: overrides?.origin ?? 'http://localhost:3300',
      'sec-fetch-site': overrides?.fetchSite ?? 'same-origin',
      'x-finco-qa-session': overrides?.qaHeader ?? '1',
    },
  }, res, next)
  return { res, next }
}

afterEach(() => vi.unstubAllGlobals())

describe('isolated local QA session plugin', () => {
  it.each([
    { ...options, enabled: false },
    { ...options, mode: 'production' },
    { ...options, frontendUrl: 'https://fincopilot.app' },
    { ...options, backendUrl: 'https://fincopilot-api.vercel.app' },
    { ...options, password: '' },
  ])('does not install a session endpoint unless isolated loopback mode is exact', config => {
    expect(createMiddleware(config)).not.toHaveBeenCalled()
  })

  it('refuses cross-origin and non-loopback requests without contacting backend', () => {
    const f = vi.fn()
    vi.stubGlobal('fetch', f)
    const registration = createMiddleware()
    const handler = registration.mock.calls[0][0] as (...args: unknown[]) => void

    for (const headers of [
      { origin: 'https://evil.example' },
      { host: 'fincopilot.app' },
      { fetchSite: 'cross-site' },
      { qaHeader: 'no' },
      { method: 'GET' },
    ]) {
      const { res } = invoke(handler, headers)
      expect(res.statusCode).not.toBe(200)
      expect(res.end).toHaveBeenCalled()
    }
    expect(f).not.toHaveBeenCalled()
  })

  it('uses the REAL backend login API and returns only its ordinary access token', async () => {
    const api = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ access_token: 'normal-jwt', token_type: 'bearer' }),
    })
    vi.stubGlobal('fetch', api)
    const registration = createMiddleware()
    const handler = registration.mock.calls[0][0] as (...args: unknown[]) => void

    const { res } = invoke(handler)
    await vi.waitFor(() => expect(res.end).toHaveBeenCalled())

    expect(res.statusCode).toBe(200)
    expect(JSON.parse(res.end.mock.calls[0][0])).toEqual({ access_token: 'normal-jwt' })
    expect(res.setHeader).toHaveBeenCalledWith('Cache-Control', 'no-store')
    const [url, request] = api.mock.calls[0]
    expect(url).toBe('http://backend:8000/api/auth/login')
    expect(request.method).toBe('POST')
    expect(request.body.get('username')).toBe(options.email)
    expect(request.body.get('password')).toBe(options.password)
  })

  it('never treats a 2FA temporary token as an authenticated session', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ requires_2fa: true, temp_token: 'pending-2fa' }),
    }))
    const registration = createMiddleware()
    const handler = registration.mock.calls[0][0] as (...args: unknown[]) => void
    const { res } = invoke(handler)
    await vi.waitFor(() => expect(res.end).toHaveBeenCalled())
    expect(res.statusCode).toBe(503)
    expect(res.end.mock.calls[0][0]).not.toContain('pending-2fa')
  })
})
