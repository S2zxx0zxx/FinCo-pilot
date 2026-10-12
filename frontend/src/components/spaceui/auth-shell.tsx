import type { ReactNode } from 'react'
import { AuthBrandPanel } from '@/components/auth-brand-panel'

/** Space UI sign-in block composition, with the real FinCo auth forms. */
export function AuthShell({ children }: { children: ReactNode }) {
  return <div className="finco-auth min-h-screen grid lg:grid-cols-[minmax(0,1fr)_minmax(0,1fr)] gap-6 lg:p-6">
    <AuthBrandPanel />
    <div className="flex min-w-0 items-center justify-center py-4 lg:py-8">{children}</div>
  </div>
}
