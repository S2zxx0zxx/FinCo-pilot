import { describe, expect, it } from 'vitest'
import {
  buildSupportUrl,
  normalizeRequestReference,
  sanitizeSupportPath,
} from './support'

describe('support navigation helpers', () => {
  it('accepts only opaque server request references', () => {
    expect(normalizeRequestReference('fcreq-a1b2c3d4e5f6')).toBe('FCREQ-A1B2C3D4E5F6')
    expect(normalizeRequestReference('Bearer secret')).toBeNull()
  })

  it('keeps diagnostic paths app-relative and drops query secrets', () => {
    expect(sanitizeSupportPath('/reset-password?token=secret')).toBe('/reset-password')
    expect(sanitizeSupportPath('https://evil.example/path')).toBeNull()
    expect(sanitizeSupportPath('//evil.example/path')).toBeNull()
  })

  it('builds a bounded support route', () => {
    expect(buildSupportUrl({
      from: '/pricing?secret=value',
      category: 'billing_payment',
      reference: 'FCREQ-A1B2C3D4E5F6',
    })).toBe('/support?from=%2Fpricing&category=billing_payment&ref=FCREQ-A1B2C3D4E5F6')
  })
})
