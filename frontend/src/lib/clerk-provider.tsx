import type { ReactNode } from 'react'
import { ClerkProvider } from '@clerk/clerk-react'
import { CLERK_PUBLISHABLE_KEY } from './clerk-config'

/** Loaded only for a configured Clerk deployment; provider settings unchanged. */
export default function ConfiguredClerkProvider({ children }: { children: ReactNode }) {
  return <ClerkProvider
    publishableKey={CLERK_PUBLISHABLE_KEY}
    signInUrl="/login"
    signUpUrl="/sign-up"
    signInFallbackRedirectUrl="/dashboard"
    signUpFallbackRedirectUrl="/dashboard"
  >{children}</ClerkProvider>
}
