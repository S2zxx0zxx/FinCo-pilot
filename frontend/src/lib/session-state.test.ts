import { beforeEach, describe, expect, it, vi } from 'vitest'
import { invalidateRejectedSession, SESSION_INVALIDATED_EVENT } from './session-state'

beforeEach(() => localStorage.clear())

describe('session rejection isolation', () => {
  it('clears only the rejected current session and notifies the same tab', () => {
    localStorage.setItem('token', 'current')
    const listener = vi.fn()
    window.addEventListener(SESSION_INVALIDATED_EVENT, listener)
    expect(invalidateRejectedSession('Bearer current')).toBe(true)
    expect(localStorage.getItem('token')).toBeNull()
    expect(listener).toHaveBeenCalledTimes(1)
    window.removeEventListener(SESSION_INVALIDATED_EVENT, listener)
  })

  it.each(['Bearer old', undefined, 'Basic other'])('preserves a new session after an unrelated rejection: %s', (header) => {
    localStorage.setItem('token', 'replacement')
    expect(invalidateRejectedSession(header)).toBe(false)
    expect(localStorage.getItem('token')).toBe('replacement')
  })
})
