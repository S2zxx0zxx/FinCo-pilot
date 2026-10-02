# FinCo-Pilot Third-Party Processor / Data-Recipient Inventory V1

**Roadmap item:** #12 — Third-party processor inventory  
**Contract ID:** `FINCO_THIRD_PARTY_PROCESSORS_V1`  
**Version:** 2026-10-02  
**Status:** inventory/engineering contract. This document does not claim that every listed vendor is legally a “processor” or that every integration is production-approved.

## 1. Purpose

FinCo-Pilot handles financial, authentication, support, billing and AI-related data. A production launch therefore needs one canonical answer to:

- which external service can receive data;
- why the data is sent;
- which data classes may cross the boundary;
- whether the service is selected, optional, unresolved or user-directed;
- whether financial or credential material can be involved;
- how disconnect/deletion is expected to work;
- which later roadmap acceptance gate still applies;
- where the provider's current public privacy/retention documentation lives.

The machine-readable source of truth is:

`backend/app/core/processor_inventory.py`

This inventory is deliberately **legally neutral**. A service may act as a processor,
independent controller/data fiduciary, regulated intermediary, infrastructure provider
or a mixed role depending on the exact product and contract. FinCo-Pilot does not guess
that classification from marketing pages. Every external personal-data boundary remains
`contract_review_required` until the relevant DPA/terms/service contract is reviewed.

## 2. Non-negotiable rules

1. **Unknown provider = not approved.** A future vendor must be added to the canonical
   registry before operator-controlled production personal data is sent to it.
2. **Selected is not the same as production accepted.** Zoho Desk and Razorpay are
   selected, but still retain release-gate work.
3. **Secrets are never inventory payloads.** API keys, OAuth refresh tokens, SMTP
   passwords, private keys and provider secrets belong in secret management, not docs,
   support tickets, analytics or public metadata.
4. **Core Copilot cannot silently route to an arbitrary upstream.** OmniRoute is the
   operator-controlled gateway; the actual upstream is a separate external recipient
   and must be explicitly approved.
5. **User-directed integrations remain separate from operator routes.** User-configured
   Advanced-Agent LLM endpoints and external MCP servers are not allowed to become the
   system-managed Core Copilot provider by accident.
6. **Disconnect is not deletion.** For bank/data providers, revoke upstream
   consent/token first, then erase local credential material and reconcile provider
   copies where supported.
7. **No full card PAN/CVV/CVC storage.** Razorpay checkout identifiers may be retained
   where required; FinCo-Pilot must not turn provider use into local Card-on-File
   storage.
8. **Public Privacy Policy comes later.** #12 creates the factual source for roadmap #27;
   it does not publish legal copy prematurely.
9. **No provider status is inferred from local config alone.** A configured key or URL
   proves only that code can call a service, not that DPA, residency, deletion,
   production terms or acceptance are complete.
10. **Provider facts can supersede older assumptions.** If current official provider
    terms conflict with an older checkpoint, provider reality wins and the retention
    contract must be corrected.

## 3. Canonical inventory

| Key | Service / boundary | Status | Personal data | Financial data | Credential/secret risk | Deletion expectation | Main remaining gates |
|---|---|---|---:|---:|---:|---|---|
| `zoho_desk` | Zoho Desk | selected, release-gated | yes | no by design | no user/provider secret should enter ticket | provider delete | #7, #12, #27, #29 |
| `razorpay` | Razorpay Payments | selected, release-gated | yes | yes | payment credentials stay provider-side | contractual retention, then minimise/delete | #12, #31–#39 |
| `pluggy` | Pluggy | optional, release-gated | yes | yes | provider token/bank auth boundary | revoke then delete | #12, #46 |
| `enable_banking` | Enable Banking | optional, release-gated | yes | yes | consent/session/private-key boundary | revoke then delete | #12, #46, #47 |
| `simplefin` | SimpleFIN / chosen server | optional, release-gated | yes | yes | access URL/token | revoke then delete | #12, #46, #48 |
| `omniroute` | operator-hosted OmniRoute | internal/self-hosted | internal route metadata | internal route metadata | dedicated inference secret | operator lifecycle | #6, #49, #50 |
| `operator_ai_upstream` | Core Copilot upstream model/search provider | unresolved | yes | potentially yes | no provider secret in prompt | unresolved until vendor selected | #6, #49, #50 |
| `user_configured_llm` | user-configured Advanced Agent endpoint | user-directed | yes | potentially yes | user connection secret stored encrypted | user-directed provider lifecycle | #12, #50 |
| `external_mcp_servers` | explicit external MCP integrations | user-directed | yes | potentially yes | scoped MCP auth | user-directed provider lifecycle | #12, #50, #51 |
| `smtp_provider` | transactional email | unresolved | yes | no by design | SMTP credential | unresolved | #17, #23, #24 |
| `object_storage_provider` | S3-compatible object storage | unresolved | yes | yes | storage credential | operator lifecycle + object delete | #16, #25, #29, #30 |
| `hosting_logging_provider` | host / proxy / log sink | unresolved | yes | no raw finance by design | host secrets | operator lifecycle | #1, #2, #25, #26, #58 |
| `managed_postgresql` | managed DB if chosen | unresolved | yes | yes | DB credential | operator lifecycle | #14, #25, #26 |
| `managed_redis` | managed Redis if chosen | unresolved | yes | normally no raw finance | Redis credential | TTL/operator lifecycle | #15, #25, #26 |
| `oidc_provider` | optional federated identity provider | unresolved | yes | no | OIDC client secret may exist | unresolved | #12, #27 |
| `open_exchange_rates` | Open Exchange Rates | no product personal data by design | no | no | app ID only | N/A for product user data | #18 |

The registry contains the exact machine-readable fields and is authoritative if this
table ever becomes stale.

## 4. Selected provider facts

### 4.1 Zoho Desk

Current FinCo-Pilot state:

- selected support platform;
- India endpoints are the configured operational direction;
- support email/portal flow was manually proven;
- direct FinCo-Pilot-to-Zoho API acceptance remains a release gate;
- an OAuth credential was previously exposed in a screenshot and must be replaced/rotated
  before production;
- open PR #13 is a separate support-hardening follow-up and must not be silently treated
  as merged while its CI remains unresolved.

Data allowed through this boundary:

- requester contact needed to reply;
- support category, subject and description;
- plan/support tier;
- severity;
- opaque FinCo-Pilot request/support reference;
- bounded safe diagnostics.

Data **not** allowed automatically:

- passwords, OTPs, OAuth/API keys, refresh tokens;
- full bank credentials;
- raw bank transaction dumps;
- full balances/account history;
- card PAN/CVV/CVC;
- arbitrary application logs.

Current official provider behavior:

- deleted Desk records normally remain in the Recycle Bin for 60 days unless an
  authorised user permanently deletes them sooner;
- Zoho publishes a separate data-retention table with provider-side deletion/backup
  stages, including 90-day backup-server periods for relevant service-data deletion
  scenarios;
- Zoho supports data-subject deletion workflows.

Sources:

- https://help.zoho.com/portal/en/kb/desk/data-administration/recycle-bin/articles/using-the-recycle-bin
- https://help.zoho.com/portal/en/kb/desk/user-management-and-security/data-security/articles/data-retention
- https://help.zoho.com/portal/en/kb/desk/user-management-and-security/compliance/articles/addressing-data-subject-requests

FinCo-Pilot action: at the #9 support-retention trigger, delete/purge through the
provider flow as promptly as permissions allow; provider backup tails remain visible
rather than falsely reporting immediate physical erasure.

### 4.2 Razorpay Payments

Current FinCo-Pilot state:

- selected payment provider;
- recurring plan mapping exists for Pro Monthly ₹99, Pro Annual ₹999 and Max Monthly
  ₹349;
- founder ₹19/₹49 payments are not recurring provider plans;
- live payment lifecycle acceptance is still roadmap #31–#39 work.

Expected data boundary:

- customer name/contact only when needed by checkout/provider flow;
- amount/currency;
- FinCo-Pilot order/reservation reference;
- Razorpay order/payment/subscription/customer identifiers;
- payment status and verification evidence.

FinCo-Pilot must **not** store full PAN/CVV/CVC.

#### Current contractual retention correction

The current Razorpay Payments merchant terms include a general merchant obligation to
retain transaction/order-related records for **10 calendar years from the relevant order
date**. The same terms also contain a narrower India/device clause mentioning a six-month
minimum for invoices/charge slips.

Because Razorpay is the selected payment provider, the 10-year merchant-record clause is
the conservative current contractual anchor for covered Razorpay transaction/order
records unless Razorpay provides a written service-specific exception. This does **not**
mean every FinCo-Pilot user record should be held for 10 years.

Source:

- https://razorpay.com/terms/

This discovery corrects the older #9 six-month-only anchor. The machine-readable
retention registry now has a separate `razorpay_transaction_order_records` rule using
10 calendar years and continues to require data minimisation.

Razorpay's buyer privacy notice also describes Razorpay Payments Private Limited as the
data fiduciary for end-customer data in that notice and says it may use third-party data
processors. FinCo-Pilot still does not generalize that wording into a legal-role
determination for every merchant integration.

Source:

- https://razorpay.com/buyer-privacy-notice/

### 4.3 Pluggy

Current code includes an optional Pluggy connector for account/transaction/balance data.
It is not an Indian AA/FIU replacement and it is not considered production accepted
merely because the connector exists.

Pluggy's current legal page describes collection/processing of high-sensitivity
financial data, including account/transaction/balance/card/loan/investment information
and provider/access credentials. It states that deletion requests are processed in
approximately 15 days, subject to legal/regulatory and other stated exceptions.

Sources:

- https://www.pluggy.ai/legal
- https://docs.pluggy.ai/en

Required before production acceptance:

- service contract/DPA/role review;
- exact countries/regions and subprocessor review for the chosen service;
- user-consent wording;
- live disconnect/revocation;
- provider-side delete request/reconciliation;
- failure/retry behavior;
- confirmation that only read scopes required by FinCo-Pilot are enabled.

### 4.4 Enable Banking

The repository contains an optional Enable Banking PSD2 connector.

The current public privacy notice is useful for the Enable Banking website/control panel,
but it does **not** by itself prove the retention/deletion terms for end-user banking API
data handled under a FinCo-Pilot commercial integration. Therefore the inventory does
not manufacture an API-data retention period from that page.

Source:

- https://enablebanking.com/privacy/

Required before production acceptance:

- service-specific API contract/DPA;
- data-region and subprocessor review;
- data-sharing-consent lifecycle;
- revoke/disconnect acceptance;
- deletion/retention terms for actual account-information data;
- roadmap #47 liability classification correctness.

### 4.5 SimpleFIN

SimpleFIN is a protocol/ecosystem boundary rather than one universal hosted processor.
The actual recipient depends on the SimpleFIN server/Bridge selected by the user.

The current SimpleFIN Bridge privacy policy states that financial-account credentials are
sent to a third-party service and that the Bridge does not store or have access to those
credentials; transaction/account information is accessed through issued tokens.

Source:

- https://beta-bridge.simplefin.org/info/privacy

FinCo-Pilot therefore must inventory the **concrete server/Bridge** used in production,
not just the protocol name. Roadmap #48 also remains responsible for classification
correctness.

## 5. AI and agent boundaries

### 5.1 OmniRoute

Operator-hosted OmniRoute is an internal gateway, not the external model processor by
itself. This classification changes if OmniRoute is later hosted as a third-party SaaS.

Core path remains:

`UI -> FinCo-Pilot AI control plane -> tools/RAG -> OmniRoute -> approved upstream`

### 5.2 Core Copilot upstream

No external upstream is approved by #12 merely because it is visible/configured inside
the local OmniRoute dashboard.

Current locally configured candidates such as OpenRouter, NVIDIA NIM, Ollama Cloud and
other development/coding/search routes remain **candidates**, not production-approved
subprocessors.

Before #6/#49/#50 can close for a chosen upstream, verify at minimum:

- exact legal entity/service;
- DPA/contract;
- prompt/tool-result retention;
- whether request content is used for model training;
- regional processing/data residency;
- subprocessors;
- deletion controls;
- security certifications relevant to the actual plan;
- cost/rate limits;
- streaming/tool-calling reliability;
- failure/fallback behavior;
- explicit rule that failure cannot silently route into an unapproved paid model.

### 5.3 User-configured LLM endpoints

Advanced/custom Agent connections are a separate user-directed boundary. They may send
the context the user explicitly configured to an external LLM endpoint.

They must never silently become Core Copilot's operator route.

### 5.4 External MCP

External MCP servers are another explicit user/operator-configured data recipient.
Unknown MCP tools stay hidden from Core Copilot by default. Tool arguments/results may
contain sensitive financial context, so an external MCP connection must remain explicit
and scoped.

## 6. Infrastructure boundaries not selected yet

The following provider names must remain **unresolved** until their roadmap item selects
the real service:

### Hosting / logging

No production host/log sink is selected. Therefore FinCo-Pilot cannot yet truthfully
claim:

- a specific hosting company;
- India log residency;
- provider log-deletion behavior;
- backup topology;
- DPA/subprocessor terms.

### PostgreSQL

The application supports PostgreSQL. Whether this becomes a third-party processor
depends on whether production uses self-hosted PostgreSQL or a managed vendor.

### Redis/workers

Same rule: self-hosted Redis is internal; managed Redis becomes an external provider.
Ephemeral authentication/OAuth/rate-limit state must retain explicit TTLs and remain out
of backups regardless.

### Object storage

The code supports S3-compatible storage, but the real vendor is unresolved. A production
choice must document:

- region;
- versioning;
- lifecycle expiration;
- delete semantics;
- multipart/temp objects;
- backup/replication behavior;
- encryption;
- processor terms.

### SMTP

No transactional email vendor is selected. #17 must identify the provider before
Privacy Policy publication.

### OIDC

OIDC is optional and no production identity provider is selected. Local auth remains a
separate first-party path.

## 7. External services that are not product-personal-data processors by design

### Open Exchange Rates

Current implementation sends an app credential and requested currency-symbol list to
retrieve reference FX rates. It does not send user IDs, account IDs, balances,
transactions or workspace data.

Provider privacy source:

- https://openexchangerates.org/privacy

If future code sends user-specific data, this classification must be re-reviewed.

### Public market/reference sources

Any public market/reference feed that receives only a generic public-data request should
not be mislabeled as a personal-data processor. Network metadata still exists at the
transport layer and normal provider/privacy terms still apply.

## 8. Dynamic-recipient rule

FinCo-Pilot contains flexible integration primitives:

- OpenAI-compatible custom LLM URLs;
- user-configured provider connections;
- external MCP servers;
- SimpleFIN server URLs;
- optional OIDC providers;
- future infrastructure vendors.

These cannot be handled by pretending every possible hostname is pre-approved.

Later runtime enforcement should distinguish:

1. **operator-controlled Core production route** — allowlist only reviewed recipients;
2. **user-directed integration** — explicit user action + disclosure + scoped permissions;
3. **internal self-hosted route** — no third-party recipient, but normal security/retention
   still applies;
4. **unknown operator-controlled route** — fail closed.

#12 establishes this policy contract. Runtime enforcement can be added at the relevant
provider/deployment roadmap gates without broadly breaking existing development paths.

## 9. Deletion and processor orchestration contract

A future #29/#30 deletion worker must not simply delete local SQL and declare success.

For each external recipient involved in the target user's lifecycle it must know:

- whether there is a revoke API;
- whether there is a delete API/admin workflow;
- whether deletion is asynchronous;
- what provider reference proves the request;
- which contractual/legal retention exception still applies;
- when retry is safe;
- how uncertain outcomes are reconciled;
- whether provider backup tails remain after active deletion.

Provider failures remain visible/retryable. A provider timeout is not evidence of
deletion.

## 10. Privacy Policy input for roadmap #27

The future published Privacy Policy should be generated from the **production-resolved**
version of this inventory, not copied from this engineering document blindly.

Before publication, replace unresolved classes with the actual chosen services for:

- hosting/logging;
- database/Redis if managed;
- object storage;
- SMTP;
- production AI upstream;
- OIDC if enabled;
- FX provider if different from the current code path.

Optional bank connectors should be disclosed only according to what production actually
offers and how user consent works.

## 11. Release-gate checklist

#12 engineering acceptance requires:

- machine-readable registry exists and fails closed for unknown keys;
- selected vendors are distinguished from production acceptance;
- every external high-sensitivity boundary has roadmap gates;
- bank connectors require revoke-then-delete semantics;
- Core Copilot upstream remains unresolved until #6/#49/#50;
- user-directed LLM/MCP boundaries remain distinct from Core routing;
- unresolved infrastructure vendors are not fabricated;
- retention contract is corrected for current Razorpay merchant terms;
- official provider links are recorded for the reviewed facts;
- tests cover registry invariants;
- hardening report is updated;
- branch CI is green;
- post-merge main CI is green.

This does **not** prove live provider deletion, production DPA execution, production
hosting residency, or published legal text. Those remain later roadmap acceptance gates.
