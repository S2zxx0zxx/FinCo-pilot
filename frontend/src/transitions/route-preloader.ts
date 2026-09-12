type RouteLoader = () => Promise<unknown>

const routeLoaders: Array<[RegExp, RouteLoader]> = [
  [/^\/$/, () => import('@/pages/dashboard')],
  [/^\/transactions(?:\/|$)/, () => import('@/pages/transactions')],
  [/^\/accounts\/[^/]+/, () => import('@/pages/account-detail')],
  [/^\/accounts(?:\/|$)/, () => import('@/pages/accounts')],
  [/^\/import(?:\/|$)/, () => import('@/pages/import')],
  [/^\/rules(?:\/|$)/, () => import('@/pages/rules')],
  [/^\/categories(?:\/|$)/, () => import('@/pages/categories')],
  [/^\/collections(?:\/|$)/, () => import('@/pages/collections')],
  [/^\/budgets(?:\/|$)/, () => import('@/pages/budgets')],
  [/^\/recurring(?:\/|$)/, () => import('@/pages/recurring')],
  [/^\/goals(?:\/|$)/, () => import('@/pages/goals')],
  [/^\/assets(?:\/|$)/, () => import('@/pages/assets')],
  [/^\/reports(?:\/|$)/, () => import('@/pages/reports')],
  [/^\/payees(?:\/|$)/, () => import('@/pages/payees')],
  [/^\/groups\/[^/]+/, () => import('@/pages/group-detail')],
  [/^\/groups(?:\/|$)/, () => import('@/pages/groups')],
  [/^\/invoices\/[^/]+/, () => import('@/pages/invoice-detail')],
  [/^\/invoices(?:\/|$)/, () => import('@/pages/invoices')],
  [/^\/workspace\/settings/, () => import('@/pages/workspace-settings')],
  [/^\/admin(?:\/|$)/, () => import('@/pages/admin/settings')],
  [/^\/agents\/connections/, () => import('@/pages/agent-connections')],
  [/^\/agents\/[^/]+/, () => import('@/pages/agent-detail')],
  [/^\/agents(?:\/|$)/, () => import('@/pages/agents-list')],
  [/^\/setup(?:\/|$)/, () => import('@/pages/setup')],
  [/^\/login(?:\/|$)/, () => import('@/pages/login')],
  [/^\/register(?:\/|$)/, () => import('@/pages/register')],
]

const warmed = new Set<RouteLoader>()

export function preloadRoute(pathname: string) {
  const loader = routeLoaders.find(([pattern]) => pattern.test(pathname))?.[1]
  if (!loader || warmed.has(loader)) return
  warmed.add(loader)
  void loader().catch(() => warmed.delete(loader))
}

function routeFromEvent(event: Event) {
  const target = event.target
  if (!(target instanceof Element)) return null
  const anchor = target.closest<HTMLAnchorElement>('a[href]')
  if (!anchor || anchor.target === '_blank' || anchor.hasAttribute('download')) return null

  try {
    const url = new URL(anchor.href, window.location.href)
    if (url.origin !== window.location.origin) return null
    return url.pathname
  } catch {
    return null
  }
}

/**
 * Warms React.lazy chunks when the user signals navigation intent.
 * Desktop gets time between hover/focus and click; touch devices start on
 * pointer-down. This does not fetch financial API data or force extra routes
 * on metered connections.
 */
export function initRoutePreloading() {
  const warmFromEvent = (event: Event) => {
    const pathname = routeFromEvent(event)
    if (pathname) preloadRoute(pathname)
  }

  document.addEventListener('pointerover', warmFromEvent, { passive: true })
  document.addEventListener('pointerdown', warmFromEvent, { passive: true })
  document.addEventListener('focusin', warmFromEvent)

  return () => {
    document.removeEventListener('pointerover', warmFromEvent)
    document.removeEventListener('pointerdown', warmFromEvent)
    document.removeEventListener('focusin', warmFromEvent)
  }
}
