const ROUTE_LABELS: Array<[RegExp, string]> = [
  [/^\/$/, 'Dashboard'],
  [/^\/transactions/, 'Transactions'],
  [/^\/accounts/, 'Accounts'],
  [/^\/import/, 'Import'],
  [/^\/rules/, 'Rules'],
  [/^\/categories/, 'Categories'],
  [/^\/collections/, 'Collections'],
  [/^\/budgets/, 'Budgets'],
  [/^\/recurring/, 'Recurring'],
  [/^\/goals/, 'Goals'],
  [/^\/assets/, 'Assets'],
  [/^\/reports/, 'Reports'],
  [/^\/payees/, 'Payees'],
  [/^\/groups/, 'Groups'],
  [/^\/invoices/, 'Invoices'],
  [/^\/workspace/, 'Workspace'],
  [/^\/admin/, 'Admin'],
  [/^\/agents/, 'AI Agents'],
  [/^\/setup/, 'Setup'],
  [/^\/login/, 'Sign in'],
  [/^\/register/, 'Create account'],
]

export function routeDestinationLabel(pathname: string) {
  return ROUTE_LABELS.find(([pattern]) => pattern.test(pathname))?.[1] ?? 'FinCo-Pilot'
}
