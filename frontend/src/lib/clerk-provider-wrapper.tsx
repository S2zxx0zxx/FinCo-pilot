import { type ReactNode } from 'react'
import { ClerkProvider } from '@clerk/clerk-react'

export const CLERK_PUBLISHABLE_KEY =
  (import.meta.env.VITE_CLERK_PUBLISHABLE_KEY as string | undefined) ||
  (import.meta.env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY as string | undefined) ||
  ''
export const isClerkConfigured = Boolean(CLERK_PUBLISHABLE_KEY && CLERK_PUBLISHABLE_KEY.trim())

export function ClerkProviderWrapper({ children }: { children: ReactNode }) {
  if (!isClerkConfigured) {
    return <>{children}</>
  }

  return (
    <ClerkProvider publishableKey={CLERK_PUBLISHABLE_KEY}>
      {children}
    </ClerkProvider>
  )
}
