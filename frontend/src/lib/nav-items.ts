import {
  ArrowLeftRight,
  BarChart3,
  Building2,
  CreditCard,
  Landmark,
  PiggyBank,
  Receipt,
  Repeat,
  SlidersHorizontal,
  Split,
  Tag,
  Target,
  Upload,
  Users,
} from 'lucide-react'
// Relative, not aliased: this file is pulled into the test project,
// which compiles without the `@/*` path mapping (see tsconfig.node.json).
import type { ModuleId } from './modules'

/**
 * Sidebar destinations. Lives outside `app-layout.tsx` so the filtering
 * below can be tested without mounting the whole layout.
 *
 * Workspace-module links carry the module they belong to. App-level links
 * (currently Plan & Billing) deliberately omit `module`: pricing must remain
 * reachable even when a workspace has a restricted module catalog.
 */
export type NavItem =
  | { type: 'link'; key: string; path: string; icon: React.ElementType; module?: ModuleId }
  | { type: 'separator'; labelKey: string }

export const navItems: NavItem[] = [
  // The dashboard ("Painel") is now reachable by clicking the FinCo-Pilot
  // logo + name in the sidebar header — no dedicated menu item to keep
  // the sidebar focused on the main destinations. Transactions sits
  // inside the ACCOUNTS section since it's account-scoped data.
  { type: 'separator', labelKey: 'nav.groupAccounts' },
  { type: 'link', key: 'transactions', path: '/transactions', icon: ArrowLeftRight, module: 'transactions' },
  { type: 'link', key: 'invoices', path: '/invoices', icon: Receipt, module: 'invoices' },
  { type: 'link', key: 'accounts', path: '/accounts', icon: Building2, module: 'accounts' },
  { type: 'link', key: 'import', path: '/import', icon: Upload, module: 'import' },
  { type: 'separator', labelKey: 'nav.groupAnalysis' },
  { type: 'link', key: 'reports', path: '/reports', icon: BarChart3, module: 'reports' },
  { type: 'link', key: 'assets', path: '/assets', icon: Landmark, module: 'assets' },
  { type: 'separator', labelKey: 'nav.groupSetup' },
  { type: 'link', key: 'budgets', path: '/budgets', icon: PiggyBank, module: 'budgets' },
  { type: 'link', key: 'goals', path: '/goals', icon: Target, module: 'goals' },
  { type: 'link', key: 'recurring', path: '/recurring', icon: Repeat, module: 'recurring' },
  { type: 'link', key: 'categories', path: '/categories', icon: Tag, module: 'categories' },
  { type: 'link', key: 'payees', path: '/payees', icon: Users, module: 'payees' },
  { type: 'link', key: 'splitGroups', path: '/groups', icon: Split, module: 'split_groups' },
  { type: 'link', key: 'rules', path: '/rules', icon: SlidersHorizontal, module: 'rules' },
  { type: 'separator', labelKey: 'nav.groupPersonal' },
  { type: 'link', key: 'planBilling', path: '/pricing', icon: CreditCard },
]

/**
 * Drop links whose workspace module is off, then drop any section header left
 * with nothing under it. App-level links have no module and always survive.
 */
export function visibleNavItems(
  items: NavItem[],
  hasModule: (id: ModuleId) => boolean,
): NavItem[] {
  const kept = items.filter(
    (item) => item.type !== 'link' || item.module === undefined || hasModule(item.module),
  )
  return kept.filter((item, index) => {
    if (item.type !== 'separator') return true
    // Links always follow their own header, so the item right after a
    // header is either one of its links or the next header.
    const next = kept[index + 1]
    return next !== undefined && next.type === 'link'
  })
}
