import { lazy, Suspense, type ReactNode } from 'react'
import { useMediaQuery } from '@/hooks/spaceui/use-media-query'

const AuthBrandPanel = lazy(() => import('@/components/auth-brand-panel').then(module => ({ default: module.AuthBrandPanel })))

/** Space UI sign-in block composition, with the real FinCo auth forms. */
export function AuthShell({ children }: { children: ReactNode }) {
  const showBrand = useMediaQuery('(min-width: 1024px)')
  return <main className="finco-auth min-h-screen grid lg:grid-cols-[minmax(0,1fr)_minmax(0,1fr)] gap-6 lg:p-6">
    {showBrand && <Suspense fallback={<div aria-hidden="true" className="rounded-3xl bg-muted min-h-[36rem]" />}><AuthBrandPanel /></Suspense>}
    <div className="flex min-w-0 items-center justify-center py-4 lg:py-8">{children}</div>
  </main>
}
