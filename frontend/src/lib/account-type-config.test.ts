import { describe, expect, it } from 'vitest'
import { getAccountTypeConfig } from './account-type-config'

describe('provider loan account presentation', () => {
  it('labels loans as liabilities instead of falling back to checking', () => {
    expect(getAccountTypeConfig('loan').label).toBe('accounts.typeLoan')
    expect(getAccountTypeConfig('loan').label).not.toBe(getAccountTypeConfig('checking').label)
  })
})
