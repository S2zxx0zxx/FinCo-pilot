import { beforeEach, describe, expect, it, vi } from 'vitest'
import { renderHook } from '@testing-library/react'
import { useClerkCustomAuth } from '@/lib/clerk-auth-adapter'

const sdk = vi.hoisted(() => ({
  signIn: { create: vi.fn(), authenticateWithRedirect: vi.fn() },
  signUp: { create: vi.fn(), prepareEmailAddressVerification: vi.fn(), attemptEmailAddressVerification: vi.fn() },
  setActive: vi.fn(), getToken: vi.fn(),
}))
vi.mock('@clerk/clerk-react', () => ({
  useSignIn: () => ({ signIn: sdk.signIn, setActive: sdk.setActive, isLoaded: true }),
  useSignUp: () => ({ signUp: sdk.signUp, setActive: sdk.setActive, isLoaded: true }),
  useClerk: () => ({ session: null }),
  useAuth: () => ({ getToken: sdk.getToken }),
}))
beforeEach(() => vi.resetAllMocks())

describe('Clerk signup requirements', () => {
  it('routes a verified Google account missing username to completion rather than another email verification', async () => {
    sdk.signUp.create.mockResolvedValue({ status: 'missing_requirements', missingFields: ['username'], unverifiedFields: [] })
    const { result } = renderHook(() => useClerkCustomAuth())
    expect(await result.current.signUpWithPassword('new@example.com', 'long-password')).toEqual({ status: 'needs_requirements' })
    expect(sdk.signUp.prepareEmailAddressVerification).not.toHaveBeenCalled()
    expect(sdk.setActive).not.toHaveBeenCalled()
  })
  it('still verifies email when that is the only outstanding requirement', async () => {
    sdk.signUp.create.mockResolvedValue({ status: 'missing_requirements', missingFields: [], unverifiedFields: ['email_address'] })
    const { result } = renderHook(() => useClerkCustomAuth())
    expect(await result.current.signUpWithPassword('new@example.com', 'long-password')).toEqual({ status: 'needs_verification' })
    expect(sdk.signUp.prepareEmailAddressVerification).toHaveBeenCalledWith({ strategy: 'email_code' })
  })
  it('does not classify a verified email with a missing username as an invalid email code', async () => {
    sdk.signUp.attemptEmailAddressVerification.mockResolvedValue({ status: 'missing_requirements', missingFields: ['username'] })
    const { result } = renderHook(() => useClerkCustomAuth())
    expect(await result.current.verifyEmailCode('123456')).toEqual({ status: 'needs_requirements' })
    expect(sdk.setActive).not.toHaveBeenCalled()
  })
  it('does not silently return an empty session token', async () => {
    sdk.getToken.mockResolvedValue(null)
    const { result } = renderHook(() => useClerkCustomAuth())
    await expect(result.current.acquireSessionToken()).rejects.toThrow('No active Clerk session token')
  })
})
