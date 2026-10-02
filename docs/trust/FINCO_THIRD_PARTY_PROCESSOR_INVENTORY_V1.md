# FinCo-Pilot Third-Party Processor Inventory V1

**Roadmap:** #12 — Third-party processor inventory  
**Contract:** `FINCO_THIRD_PARTY_PROCESSOR_INVENTORY_V1`  
**Version:** 2026-10-02  
**Status:** engineering inventory contract; actual production activation remains deployment/provider specific.

This document is the human-readable companion to the canonical machine-readable registry in `backend/app/core/processor_inventory.py`. It records every repository-known external service that may receive FinCo-Pilot data or production request metadata. It is deliberately stricter than a marketing subprocessor list: unresolved hosting, AI and operator-selected vendors remain visible until the exact production provider is known.

This inventory does **not** claim that every listed service is currently active, nor does it decide the legal processor/controller classification of a provider. Those conclusions depend on the actual deployment, contract, purpose and jurisdiction. It exists so FinCo-Pilot cannot silently introduce a provider and later discover that its retention/deletion/privacy posture was never reviewed.

## 1. Inventory rules

1. **Activation is deployment-specific.** A provider being present in source code does not mean it is active in production.
2. **Unknown provider = release blocker.** Any production service that can receive user or operational data must be represented here before activation.
3. **No secrets in the inventory.** Never store API keys, OAuth tokens, client secrets, passwords, signing keys, access tokens, refresh tokens or bank credentials here.
4. **Data minimisation is part of provider approval.** Only the minimum fields required for the provider purpose may leave FinCo-Pilot.
5. **Deletion must extend to provider copies.** Roadmap #9 retention rules apply to provider-side copies where the provider stores user data.
6. **High-risk processors need explicit acceptance.** Support, payments, banking, storage, email, authentication and external AI require operator review of retention/deletion, geography/access and contract/DPA position before public production.
7. **Provider failure must not weaken product safety.** A missing provider cannot justify exposing secrets, bypassing permissions, fabricating financial facts or silently sending data elsewhere.
8. **New integrations update both files.** Add the machine-readable entry and this human explanation in the same change.

## 2. Classification vocabulary

- `processor_when_enabled` — expected to process user/personal/product data when the integration is enabled.
- `unresolved_processor` — category is expected to process sensitive data, but the exact production provider/legal entity is not yet fixed.
- `service_vendor_review` — external service normally receives narrow technical/reference requests rather than the user's primary finance record, but still needs provider/terms/privacy review.
- `conditional` — known integration, inactive unless the corresponding feature/configuration is enabled.
- `operator_configured` — generic slot; the actual vendor name must be recorded before production.
- `unresolved` — launch dependency is intentionally open and cannot be treated as approved.

## 3. Current inventory

| ID | Service | Purpose | Data exposure | Current launch position |
| --- | --- | --- | --- | --- |
| `zoho_desk` | Zoho Desk | Customer support | Email, user/support metadata, support text, safe diagnostics | Conditional; real support account exists, direct API activation remains subject to current credential/smoke-test state |
| `razorpay` | Razorpay | Checkout/subscriptions | Billing/payment/customer/provider identifiers | Conditional; payment lifecycle acceptance remains separate roadmap work |
| `pluggy` | Pluggy | Bank/open-finance sync | Accounts, balances, transactions, institution/provider identifiers | Optional/conditional |
| `enable_banking` | Enable Banking | Open-banking sync | Consent/session, accounts, balances, transactions | Optional/conditional |
| `simplefin` | SimpleFIN | Read-only finance sync | Accounts, balances, transactions, institutions | Optional/conditional |
| `smtp_provider` | Operator-selected SMTP | Verification/recovery email | Email address, message content, reset/verification links | Exact vendor unresolved until #17 |
| `object_storage` | Operator-selected S3-compatible storage | Attachments/documents | Uploaded financial documents and object metadata | Exact vendor unresolved until #16 |
| `oidc_provider` | Operator-selected OIDC IdP | Federated login | Subject/email/profile/role claims | Optional/operator configured |
| `openexchangerates` | OpenExchangeRates | FX rates | Currency/rate request metadata | Conditional |
| `yahoo_finance` | Yahoo Finance via yfinance | Market search/prices | Ticker queries and request metadata | Conditional |
| `tesouro_direto` | Tesouro Direto public source | Treasury reference prices | Public bond/reference request metadata | Conditional |
| `ai_llm_route` | Exact approved external AI route TBD | AI assistance | Prompt/context/tool output; may include financial data | **Unresolved high-risk gate** until #6/#49/#50 |
| `hosting_provider` | Production hosting/network provider TBD | Production infrastructure | Traffic, logs and hosted app data depending on architecture | **Unresolved high-risk gate** until #1/#2 |
| `github_private_vulnerability_reporting` | GitHub PVR | Security reports | Reporter/contact and technical vulnerability details | Conditional, separate from normal support |

The Python registry is authoritative for machine validation; this table is the readable operational summary.

## 4. High-risk provider contracts

### 4.1 Support — Zoho Desk

The Support & Trust Layer intentionally sends only bounded support data:

- requester email;
- support subject/message;
- authenticated user ID;
- effective plan/support tier;
- category/severity;
- page/app/locale/request references;
- bounded User-Agent metadata.

The application does not automatically attach balances, raw statements, transaction history, bank credentials, passwords, OTPs, card secrets, API keys or OAuth tokens. Provider-side retention/deletion still has to fit `FINCO_DATA_RETENTION_V1`.

### 4.2 Payments — Razorpay

Razorpay is a conditional payment processor integration. The inventory does not claim Live Mode, recurring subscriptions, webhook acceptance or tax treatment are complete. Before payment launch, the operator must verify the exact customer/payment fields sent, webhook/event storage, refund/cancellation lifecycle and records that must be retained for legitimate payment/accounting purposes.

### 4.3 Banking/open finance

Pluggy, Enable Banking and SimpleFIN can expose the highest-sensitivity product data: account identifiers, balances and transactions. Each enabled provider requires a production acceptance record covering:

- consent/connect/reconnect/revocation;
- access scope;
- provider token/credential storage;
- account/liability classification;
- retention/deletion/export;
- duplicate/retry behavior;
- geographic/provider eligibility.

The planned Indian AA/FIU route is **not** represented as an active processor yet because roadmap #5/#40–45 has not selected and accepted a production partner. Once selected, it must receive its own registry entry before activation.

### 4.4 Transactional email

`smtp_provider` is a generic slot, not a provider claim. Before roadmap #17 is closed, replace the operational record with the actual SMTP vendor/service, region, delivery-log retention, suppression/bounce behavior and deletion/contract position.

### 4.5 Object storage

`object_storage` is also a generic slot. If production stays on local durable volumes, no third-party object-storage processor is active for those files. If `STORAGE_PROVIDER=s3`, the actual vendor/region/bucket lifecycle, encryption/access policy, backup replication and deletion semantics must be recorded before launch.

### 4.6 OIDC

If OIDC is enabled, the operator must record the actual identity provider and claim set. Only required claims should be requested. Account-linking mode and role/group sync materially change the data exchanged and must be covered by the deployment record.

### 4.7 External AI/LLM

This is an explicit unresolved high-risk gate. Code support for AI or OmniRoute does not mean every configured provider is approved to receive FinCopilot user context.

Before external production inference is enabled:

- pin the exact provider legal/service identity and model route;
- verify training-on-prompts policy and retention/logging terms;
- verify geography/subprocessors where relevant;
- define deletion/export behavior;
- minimise retrieved context/tool outputs;
- keep deterministic finance truths such as Safe-to-Spend outside the LLM;
- do not allow broad silent fallback to an unreviewed provider;
- record each materially distinct provider in this inventory.

Self-hosted/local inference that does not transmit data to a third party is not a third-party processor, although its infrastructure still falls under the hosting/storage inventory.

### 4.8 Hosting

The production hosting provider remains unresolved while roadmap #1/#2 is deferred. Before public launch, record:

- provider/service and legal entity;
- deployment region(s);
- network/application logs;
- managed database/cache/storage services used;
- backup locations/lifecycle;
- staff/support access model;
- deletion/export procedure;
- contract/DPA position where applicable.

No "India hosted" or similar residency claim may be published without evidence for the actual production stack.

## 5. Lower-data service vendors

OpenExchangeRates, Yahoo Finance/yfinance and Tesouro Direto are not treated here as automatically equivalent to banking/payment/support processors. FinCopilot should send only narrow reference requests to these services. Ticker searches can still reveal portfolio interests, so they are not considered zero-information requests.

If a future implementation begins sending user identity, account IDs, portfolio quantities or transaction records to one of these services, its classification must be upgraded and reviewed before deployment.

## 6. Relationship to retention and deletion

This inventory is coupled to `FINCO_DATA_RETENTION_V1`:

- deleting a local row is not enough when a provider holds a copy;
- provider deletion APIs/manual procedures must be known before high-risk activation;
- provider retention that cannot satisfy the product lifecycle becomes a contract/launch blocker;
- backups/provider logs need explicit lifecycle handling rather than being ignored.

Roadmap #10 and #11 define user/shared-workspace ownership semantics. Later implementation items #29/#30 must make provider-side deletion/revocation part of the executable deletion workflow where applicable.

## 7. Deployment acceptance record

For every production deployment, create a private operator record containing **non-secret facts only**:

- inventory entry ID;
- actual provider/service/legal name;
- feature enabled/disabled;
- account/data-center/region;
- categories of data actually sent;
- provider privacy/retention/deletion references and review date;
- contract/DPA status if applicable;
- operator owner;
- date of last live smoke test;
- deletion/export procedure location.

Secrets stay in deployment secret storage and must never be copied into that record.

## 8. Change-control gate

A PR that introduces a new outbound service capable of receiving user/operational data must also:

1. add/update `backend/app/core/processor_inventory.py`;
2. document data categories and activation condition;
3. set the correct sensitivity/classification;
4. state provider deletion/retention review requirements;
5. keep secrets out of source;
6. update retention/deletion behavior if a persistent provider copy is introduced.

The contract tests under `backend/tests/test_processor_inventory.py` guard the current known provider set, fail-closed lookup behavior and high-risk boundary classifications. It is intentionally not a legal-compliance oracle; it is an engineering drift detector.

## 9. Roadmap #12 closure criteria

Roadmap #12 is engineering-complete when:

- all repository-known external provider classes are inventoried;
- unresolved production provider slots are visible rather than guessed;
- high-risk providers are distinguished from reference-data vendors;
- every entry has activation condition, data categories, sensitivity, deletion review and retention linkage;
- secrets are excluded;
- the canonical machine-readable Python registry is validated in CI;
- the hardening report records the processor inventory as defined.

This does **not** close hosting (#1/#2), SMTP (#17), object storage (#16), AI production acceptance (#6/#49/#50), payment lifecycle (#31–39), privacy policy (#27) or executable deletion (#29/#30).
