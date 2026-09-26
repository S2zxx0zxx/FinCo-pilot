# FinCo Copilot Control Plane V1

Status: implementation contract for the built-in FinCo Copilot.  
Scope: provider-independent product behavior, data/tool policy, UX, and safety boundaries.  
Out of scope: choosing the final paid production model/provider and claiming roadmap #49/#50 complete.

## 1. Product north star

FinCo Copilot is not a generic chat box added to a finance app. It is the
always-available control surface for FinCo-Pilot.

The target experience is:

- The user can open one small Copilot entry point from any authenticated page.
- The Copilot knows the active workspace and current page context.
- The user should not have to repeat data already stored in FinCo-Pilot.
- The Copilot reads the minimum live data required for the current task.
- Deterministic FinCo-Pilot services remain the source of truth for financial
  calculations. The model explains those results; it does not recreate them.
- Low-friction actions become proposals the user can review and apply.
- Money movement, credentials, authentication/security settings, and permission
  bypasses are never autonomous.
- Provider/model choice remains an implementation detail behind the existing
  provider abstraction and OmniRoute-compatible gateway.

This is deliberately optimized for users who want to do less manual work:
asking a natural-language question should replace navigation, filtering,
cross-checking, and repetitive setup wherever the product can do that safely.

## 2. Architecture

```text
Every app page
    |
    v
Compact global Copilot launcher
    |
    v
System-managed per-user/per-workspace FinCo Copilot
    |
    +--> current page context (route/filter/selection orientation)
    |
    +--> minimal always-on context (locale + account orientation, no balances)
    |
    v
Agent runtime
    |
    +--> workspace role policy
    +--> billing/product capability policy
    +--> per-agent/tool policy
    +--> proposal/action policy
    +--> operational usage ceiling
    |
    v
MCP tool registry
    |
    +--> deterministic finance services
    +--> scoped read models
    +--> proposal tools
    +--> RAG/knowledge tools
    |
    v
Provider abstraction
    |
    +--> current OpenAI/Anthropic/Ollama/OpenAI-compatible adapters
    +--> OmniRoute-compatible endpoint/default model
    +--> future provider/model replacement without changing product contracts
```

The system-managed Copilot row intentionally stores no fixed provider/model.
That keeps provider replacement behind the instance-level routing boundary.

## 3. Context strategy: know more without dumping everything

"Can read everything" must not mean "send everything to the model on every
turn."

V1 uses three layers:

1. **Always-on orientation** — preferred language, currency, timezone and a
   compact account inventory. Email addresses, balances, account IDs, raw bank
   payloads, and credentials are intentionally excluded.
2. **Current page context** — route plus any page-published filters/selection.
   This helps resolve phrases such as "this transaction" or "what am I looking
   at?" Page context is orientation, never authoritative financial truth.
3. **Just-in-time tool reads** — the runtime retrieves live workspace data only
   when it is needed to answer the request.

This lowers token cost, reduces unnecessary exposure of sensitive financial
data, and makes stale context less likely.

## 4. Source-of-truth rule

The LLM is an orchestrator and explainer, not the financial ledger.

Examples:

- Safe-to-Spend -> `get_safe_to_spend` -> deterministic spending-plan service.
- Transaction totals -> SQL-backed aggregate/report tools.
- Loan schedule -> deterministic amortization service.
- Account/transaction facts -> scoped read services/tools.

If the deterministic service returns blockers, missing data, stale provider
refresh, or no headline, the Copilot must explain that state instead of
inventing a number.

## 5. Control and automation levels

### Level 0 — automatic read/explain

Allowed when the authenticated user is permitted to read the active workspace.

Examples: find transactions, explain a budget, summarize goals, show account
health, explain Safe-to-Spend blockers, inspect loan plans.

No confirmation is required because no application data is mutated.

### Level 1 — proposal-first app changes

The Copilot may prepare exact reversible changes using `propose_*` tools.
The internal tool call is a preview only. The UI must show the proposal and the
human applies it explicitly.

Examples: categorize transactions, create a category, create a budget, create a
goal, create/update recurring items.

The model must never describe a proposal as completed.

### Level 2 — future opt-in low-risk automation

Not enabled merely by this V1 contract.

Candidate automations may include repeated categorization/housekeeping,
reminders, or other reversible app-only tasks. They require an explicit user
rule/scope, an audit trail, limits, an off switch, and a deterministic rollback
or correction path where feasible.

### Level 3 — never autonomous

The Copilot must not silently:

- move or transfer money;
- authorize a payment;
- change login credentials, passkeys, 2FA, or security settings;
- reveal secrets/tokens/provider credentials;
- change workspace membership/permissions;
- bypass billing/module/role restrictions.

Provider-side confirmation and explicit human control remain authoritative.

## 6. Authorization model

Authorization is enforced below the model, not by prompt text alone.

A tool call must satisfy all applicable layers:

1. authenticated active user;
2. active workspace membership/manager access;
3. workspace role;
4. product/module availability;
5. billing capability/limit where the underlying feature requires one;
6. internal-vs-external MCP policy;
7. tool-specific risk/proposal rules;
8. quota/operational capacity limits.

The built-in core Copilot is a separate first-party surface and therefore does
not require the Max-only `agents_automation` capability. That exception does
**not** grant the Copilot paid capabilities underneath a tool. For example,
Advanced Reports still requires the Advanced Reports entitlement.

Custom agents and external MCP remain Advanced Agents/Max surfaces.

## 7. User and workspace isolation

A core Copilot belongs to one user in one workspace.

Conversation rows are scoped by both workspace and owning user. A member of the
same shared workspace cannot read another member's Copilot history merely
because both can see shared financial records.

Financial tool reads remain workspace-scoped and therefore follow the active
workspace's membership and billing-owner rules.

## 8. Tool exposure

Current core read coverage includes:

- transactions and aggregate queries;
- accounts and account summaries;
- categories and payees;
- budgets and budget-vs-actual;
- goals;
- recurring transactions/subscriptions;
- assets/investments;
- expense-sharing groups and balances;
- dashboard snapshot;
- Safe-to-Spend;
- loan plans;
- sanitized bank-connection health/freshness;
- transaction automation rules;
- account/asset collections;
- eligible advanced reports;
- global search;
- agent knowledge/RAG where configured.

Bank-connection tools must never expose credentials, access tokens, raw provider
payloads, or provider secret identifiers.

Additional module-specific read surfaces can be added behind the same policy
layer; adding a tool is not permission to bypass the module's existing rules.

## 9. Prompt-injection boundary

Retrieved application data is untrusted input.

Transaction descriptions, payee names, imported bank strings, uploaded
documents, page context, and tool/MCP output are data, not instructions. Text
inside them must not override runtime rules, workspace permissions, tool policy,
or the user's actual request.

This rule is enforced as an always-on runtime instruction and should also be
covered by adversarial tests before production launch.

## 10. UX contract

The default daily surface is the system FinCo Copilot, not the custom-agent
configuration UI.

V1 UX:

- one compact floating launcher on authenticated pages;
- keyboard shortcut remains available;
- narrow, compact slide-over chat;
- system Copilot is the default assistant;
- custom agents may appear as additional choices only when Advanced Agents is
  entitled;
- quick zero-effort prompts for Safe-to-Spend, attention items, and current-page
  explanation;
- conversation persistence per assistant;
- streaming answer/tool feedback;
- proposal cards for pending changes;
- no provider/model branding on the core Copilot empty state.

Provider choice should not feel like part of the user's normal finance workflow.

## 11. Cost and abuse controls

The core Copilot uses an operator-configurable daily message ceiling. This is an
operational protection, not a pricing promise.

The product should also preserve:

- bounded tool-call iterations;
- bounded result sizes/pagination;
- minimum necessary retrieval;
- token and latency telemetry;
- provider rate-limit/error classification;
- no raw sensitive prompt logging in ordinary observability.

Plan-specific commercial AI quotas can be changed later without changing the
core control-plane architecture.

## 12. Failure behavior

When a dependency fails:

- provider failure -> surface a useful retry/configuration error;
- MCP/tool unavailable -> answer only what can be supported, never fabricate;
- entitlement blocked -> do not substitute a hidden paid feature;
- stale/incomplete financial data -> surface freshness/blocker state;
- Safe-to-Spend blocked -> no headline amount;
- tool iteration ceiling -> return an explicit bounded failure;
- client disconnect -> accepted usage/message semantics remain deterministic.

## 13. Test/release gates for this control plane

Before this branch is merge-ready:

- backend lint/typecheck/tests green;
- frontend lint/build/tests green;
- PostgreSQL migration smoke green;
- core Copilot available on Free without unlocking Advanced Agents;
- custom agents/external MCP remain gated;
- conversation cross-user isolation covered;
- viewer chat exposes only read tools;
- hidden/disallowed tool names cannot be dispatched;
- per-tool product capability enforcement covered;
- bank connection read surface proves credentials are redacted;
- Safe-to-Spend tool proves blockers prevent a fabricated headline;
- app layout and agent service integrity checked after edits;
- OmniRoute deployment workflow stays healthy.

Production provider credentials and live model acceptance remain separate
operator/deployment work.

## 14. Roadmap relationship

This contract advances roadmap #6 by making the provider choice replaceable and
defining the product behavior around it.

It does not claim:

- #49 real production AI provider acceptance is complete; or
- #50 final production streaming/tools/RAG/error QA is complete.

Those gates require the real production endpoint/model, live secrets in a
secret manager, production acceptance tests, and final load/failure testing.
