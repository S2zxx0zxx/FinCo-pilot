import { type ReactNode } from 'react'
import { ClerkProvider } from '@clerk/clerk-react'

import { CLERK_PUBLISHABLE_KEY, isClerkConfigured } from './clerk-config'

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
