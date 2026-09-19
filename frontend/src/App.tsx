import { lazy, Suspense } from 'react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { Toaster } from '@/components/ui/sonner'
import { TooltipProvider } from '@/components/ui/tooltip'
import { ThemeProvider } from '@/components/theme-provider'
import { AuthProvider } from '@/contexts/auth-provider'
import { BillingProvider } from '@/contexts/billing-provider'
import { WorkspaceProvider } from '@/contexts/workspace-provider'
import { CollectionFilterProvider } from '@/contexts/collection-filter-provider'
import { ProtectedRoute } from '@/components/protected-route'
import { AdminRoute } from '@/components/admin-route'
import { AgentsRoute } from '@/components/agents-route'
import { ModuleRoute } from '@/components/module-route'
import { EntitlementRoute } from '@/components/entitlement-route'
import { AppLayout } from '@/components/app-layout'
import { PWAProvider } from '@/pwa/pwa-provider'
import { PWAChrome } from '@/pwa/pwa-chrome'
import { FinCoRouteLoader } from '@/transitions/finco-route-loader'
import { FinCoNavigationTransition } from '@/transitions/finco-navigation-transition'

const AccountRecovery = lazy(() => import('@/pages/account-recovery'))
const SetupPage = lazy(() => import('@/pages/setup'))
const LoginPage = lazy(() => import('@/pages/login'))
const RegisterPage = lazy(() => import('@/pages/register'))
const PricingPage = lazy(() => import('@/pages/pricing'))
const SpendingPlanPage = lazy(() => import('@/pages/spending-plan'))
const DashboardPage = lazy(() => import('@/pages/dashboard'))
const TransactionsPage = lazy(() => import('@/pages/transactions'))
const AccountsPage = lazy(() => import('@/pages/accounts'))
const AccountDetailPage = lazy(() => import('@/pages/account-detail'))
const ImportPage = lazy(() => import('@/pages/import'))
const RulesPage = lazy(() => import('@/pages/rules'))
const CategoriesPage = lazy(() => import('@/pages/categories'))
const CollectionsPage = lazy(() => import('@/pages/collections'))
const BudgetsPage = lazy(() => import('@/pages/budgets'))
const RecurringPage = lazy(() => import('@/pages/recurring'))
const GoalsPage = lazy(() => import('@/pages/goals'))
const AssetsPage = lazy(() => import('@/pages/assets'))
const ReportsPage = lazy(() => import('@/pages/reports'))
const PayeesPage = lazy(() => import('@/pages/payees'))
const GroupsPage = lazy(() => import('@/pages/groups'))
const GroupDetailPage = lazy(() => import('@/pages/group-detail'))
const AdminSettingsPage = lazy(() => import('@/pages/admin/settings'))
const AgentsListPage = lazy(() => import('@/pages/agents-list'))
const AgentDetailPage = lazy(() => import('@/pages/agent-detail'))
const AgentConnectionsPage = lazy(() => import('@/pages/agent-connections'))
const InvoicesPage = lazy(() => import('@/pages/invoices'))
const InvoiceDetailPage = lazy(() => import('@/pages/invoice-detail'))
const SharedInvoicePage = lazy(() => import('@/pages/shared-invoice'))
const WorkspaceSettingsPage = lazy(() => import('@/pages/workspace-settings'))
const OAuthCallbackPage = lazy(() => import('@/pages/oauth-callback'))
const OIDCCallbackPage = lazy(() => import('@/pages/oidc-callback'))

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 1000 * 60 * 5,
      retry: 1,
    },
  },
})

function App() {
  return (
    <ThemeProvider>
      <PWAProvider>
        <QueryClientProvider client={queryClient}>
          <TooltipProvider>
            <BrowserRouter>
              <FinCoNavigationTransition />
              <AuthProvider>
                <BillingProvider>
                  <WorkspaceProvider>
                    <Suspense fallback={<FinCoRouteLoader />}>
                      <Routes>
                        <Route path="/setup" element={<SetupPage />} />
                        <Route path="/forgot-password" element={<AccountRecovery mode="forgot" />} />
                        <Route path="/reset-password" element={<AccountRecovery mode="reset" />} />
                        <Route path="/verify-email" element={<AccountRecovery mode="verify" />} />
                        <Route path="/request-verification" element={<AccountRecovery mode="request-verification" />} />
                        <Route path="*" element={<main className="p-10 space-y-4"><h1 className="text-xl">Page not found</h1><a className="underline" href="/">Return home</a></main>} />
                        <Route path="/login" element={<LoginPage />} />
                        <Route path="/auth/oidc/callback" element={<OIDCCallbackPage />} />
                        <Route path="/register" element={<RegisterPage />} />
                        <Route path="/pricing" element={<PricingPage />} />
                        {/* A client opening a link the sender shared. Deliberately
                            outside ProtectedRoute and outside AppLayout: the
                            recipient has no account, and the token is the whole
                            credential. */}
                        <Route path="/i/:token" element={<SharedInvoicePage />} />
                        <Route
                          element={
                            <ProtectedRoute>
                              <CollectionFilterProvider>
                                <AppLayout />
                              </CollectionFilterProvider>
                            </ProtectedRoute>
                          }
                        >
                          <Route path="/" element={<DashboardPage />} />
                          <Route path="/spending-plan" element={<ModuleRoute module="accounts"><SpendingPlanPage /></ModuleRoute>} />
                          <Route path="/transactions" element={<ModuleRoute module="transactions"><TransactionsPage /></ModuleRoute>} />
                          <Route path="/accounts" element={<ModuleRoute module="accounts"><AccountsPage /></ModuleRoute>} />
                          <Route path="/accounts/:id" element={<ModuleRoute module="accounts"><AccountDetailPage /></ModuleRoute>} />
                          <Route path="/oauth/callback" element={<OAuthCallbackPage />} />
                          <Route path="/enable-banking" element={<OAuthCallbackPage />} />
                          <Route path="/import" element={<ModuleRoute module="import"><ImportPage /></ModuleRoute>} />
                          <Route path="/rules" element={<ModuleRoute module="rules"><EntitlementRoute capability="rules" title="Smart Rules are a Pro feature" description="Upgrade to Pro to create, import and manage automated categorisation rules."><RulesPage /></EntitlementRoute></ModuleRoute>} />
                          <Route path="/categories" element={<ModuleRoute module="categories"><CategoriesPage /></ModuleRoute>} />
                          <Route path="/collections" element={<CollectionsPage />} />
                          <Route path="/budgets" element={<ModuleRoute module="budgets"><BudgetsPage /></ModuleRoute>} />
                          <Route path="/goals" element={<ModuleRoute module="goals"><GoalsPage /></ModuleRoute>} />
                          <Route path="/recurring" element={<ModuleRoute module="recurring"><RecurringPage /></ModuleRoute>} />
                          <Route path="/assets" element={<ModuleRoute module="assets"><AssetsPage /></ModuleRoute>} />
                          <Route path="/assets/import" element={<Navigate to="/import?tab=investments" replace />} />
                          <Route path="/reports" element={<ModuleRoute module="reports"><EntitlementRoute capability="advanced_reports" title="Advanced Reports are a Pro feature" description="Upgrade to Pro for deeper net-worth, cash-flow and income/expense analysis."><ReportsPage /></EntitlementRoute></ModuleRoute>} />
                          <Route path="/payees" element={<ModuleRoute module="payees"><PayeesPage /></ModuleRoute>} />
                          <Route path="/groups" element={<ModuleRoute module="split_groups"><GroupsPage /></ModuleRoute>} />
                          <Route path="/groups/:id" element={<ModuleRoute module="split_groups"><GroupDetailPage /></ModuleRoute>} />
                          {/* Invoice history stays readable after a Max downgrade.
                              Backend billing guards lock mutations while module +
                              workspace role gates continue protecting the ledger. */}
                          <Route path="/invoices" element={<ModuleRoute module="invoices"><InvoicesPage /></ModuleRoute>} />
                          <Route path="/invoices/:id" element={<ModuleRoute module="invoices"><InvoiceDetailPage /></ModuleRoute>} />
                          <Route path="/workspace/settings" element={<WorkspaceSettingsPage />} />
                          <Route path="/admin" element={<AdminRoute><AdminSettingsPage /></AdminRoute>} />
                          <Route path="/agents" element={<AgentsRoute><EntitlementRoute capability="agents_automation" title="Advanced Agents are a Max feature" description="Max unlocks FinCo advanced Agents, MCP and automation when the deployment capability is enabled."><AgentsListPage /></EntitlementRoute></AgentsRoute>} />
                          <Route path="/agents/connections" element={<AgentsRoute><EntitlementRoute capability="agents_automation" title="Agent Connections are a Max feature" description="Upgrade to Max to configure advanced agent connections and automation."><AgentConnectionsPage /></EntitlementRoute></AgentsRoute>} />
                          <Route path="/agents/:id" element={<AgentsRoute><EntitlementRoute capability="agents_automation" title="Advanced Agents are a Max feature" description="Upgrade to Max to use agent workflows and MCP automation."><AgentDetailPage /></EntitlementRoute></AgentsRoute>} />
                        </Route>
                      </Routes>
                    </Suspense>
                    <Toaster />
                  </WorkspaceProvider>
                </BillingProvider>
              </AuthProvider>
            </BrowserRouter>
            <PWAChrome />
          </TooltipProvider>
        </QueryClientProvider>
      </PWAProvider>
    </ThemeProvider>
  )
}

export default App
