import { describe, expect, it } from 'vitest'
import { sanitizeSentryEvent } from './sentry'

describe('Sentry financial data minimization', () => {
  it('retains only safe exception location, type and constant component', () => {
    const input = {
      request: { url: 'https://fincopilot.app/i/secret?token=private', data: { balance: 1000 } },
      user: { email: 'private@example.com' },
      extra: { account: 'private account' },
      contexts: { account: 'private account' },
      breadcrumbs: [{ message: 'card 4111' }],
      transaction: '/accounts/private-id',
      exception: { values: [{
        type: 'TypeError', value: 'card 4111 in private account',
        stacktrace: { frames: [{ filename: 'https://site/app.js?token=private', lineno: 17,
          vars: { card: '4111' }, context_line: 'const secret = "4111"' }] },
      }] },
    }
    const value = sanitizeSentryEvent(input)
    expect(JSON.stringify(value)).not.toMatch(/4111|private|balance|account|token|1000/)
    expect(value.exception.values[0].type).toBe('TypeError')
    expect(value.exception.values[0].stacktrace.frames[0].lineno).toBe(17)
    expect(value.exception.values[0].stacktrace.frames[0].filename).toBe('https://site/app.js')
    expect((value as unknown as { tags: { component: string } }).tags).toEqual({ component: 'web' })
  })
})
