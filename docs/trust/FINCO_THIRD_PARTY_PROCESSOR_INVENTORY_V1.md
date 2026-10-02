# FinCo-Pilot Third-Party Processor / Data-Recipient Inventory V1

**Roadmap:** #12 — Third-party processor inventory  
**Contract:** `FINCO_THIRD_PARTY_PROCESSOR_INVENTORY_V1`  
**Version:** 2026-10-02  
**Status:** engineering inventory contract; production activation remains provider/deployment specific.

The canonical machine-readable source is:

`backend/app/core/processor_inventory.py`

This document is the human-readable operational companion. It records external data boundaries without pretending that every service is active or that every vendor has the same legal role.

## 1. Rules

1. Unknown operator-controlled recipients are not approved.
2. Source-code support does not equal production activation.
3. No API key, OAuth token, password, private key, bank credential, SMTP secret or provider credential belongs in this inventory.
4. High-sensitivity providers require explicit retention/deletion and contract review before launch.
5. Provider-side copies must remain compatible with `FINCO_DATA_RETENTION_V1`.
6. Core Copilot may not silently route to an unreviewed external AI upstream.
7. User-directed LLM/MCP connections remain separate from the operator-controlled Core route.
8. A provider outage never justifies bypassing permissions, exposing secrets or fabricating financial data.
9. If a new external service is added, the registry and its tests must be updated in the same change.

## 2. Current boundaries

### Selected but still release-gated

- **Zoho Desk** — customer support.
  - Can receive requester contact, support text, support tier/severity and bounded safe diagnostics.
  - Must not automatically receive raw balances, transaction dumps, passwords, OTPs, bank credentials or OAuth/API secrets.
  - Live app-to-provider acceptance and provider deletion behavior remain separate gates.

- **Razorpay Payments** — payment/order/subscription lifecycle.
  - May receive customer/payment/order/subscription identifiers and amount/currency metadata.
  - FinCo-Pilot must not persist full PAN/CVV/CVC.
  - Live checkout, webhook, subscription, refund/cancellation and record-retention acceptance remain roadmap #31–#39.

### Optional banking/open-finance boundaries

- **Pluggy**
- **Enable Banking**
- **SimpleFIN / the concrete selected SimpleFIN server**

These can receive high-sensitivity financial data such as accounts, balances, transactions and provider connection identifiers. Production use requires live connect/revoke/delete testing and provider-specific retention/contract review.

SimpleFIN is a protocol/ecosystem boundary, not one universal vendor. The actual server/bridge used in production must be identified.

### AI and agent boundaries

- **Operator-hosted OmniRoute** is treated as an internal routing/control boundary when self-hosted.
- The **production Core Copilot external upstream** remains unresolved until #6/#49/#50 selects and accepts the exact provider/model route.
- **User-configured Advanced Agent LLM endpoints** are explicit user-directed recipients.
- **External MCP servers** are also explicit user/operator-directed recipients.

No locally configured model/provider becomes production-approved merely because it exists in an OmniRoute dashboard.

### Selected managed PostgreSQL boundary

- **Neon Postgres** is selected for the zero-cost roadmap #14 production database path.
- The selection remains release-gated until the actual project/region is provisioned, the
  direct provider endpoint is stored only through roadmap #13 secret management, migrations
  pass and the credential-safe production PostgreSQL acceptance probe succeeds.
- Neon provider history/PITR is not treated as proof of FinCo-Pilot disaster recovery;
  roadmap #25 still requires an isolated restore rehearsal.

### Selected object-storage boundary

- **Cloudflare R2** is selected for the zero-cost roadmap #16 production object-storage path.
- The bucket remains private and FinCo-Pilot uses R2's S3-compatible API with bucket-scoped Object Read & Write credentials.
- Selection remains release-gated until the operator-owned bucket, exact endpoint/jurisdiction, secret-managed credentials and the credential-safe upload/read/delete acceptance probe pass.
- R2 location hints/jurisdictions are not treated as an India-residency guarantee.
- Roadmap #25 still owns isolated backup/restore proof; selecting R2 does not close disaster recovery.

### Infrastructure boundaries still unresolved

The inventory intentionally leaves these unresolved until their roadmap items select the real vendor:

- production hosting / reverse proxy / log sink;
- managed Redis, if used;
- transactional SMTP;
- optional OIDC provider.

Self-hosted PostgreSQL/Redis/object services are not third-party processors merely because the software exists. Managed service selection changes the boundary.

### Reference-data services

Current design treats these as narrow external reference-data calls, not primary product-personal-data processors:

- Open Exchange Rates;
- Yahoo Finance via yfinance;
- Tesouro Direto public market-data source.

If future code starts sending user identity, account IDs, portfolio quantities or transaction records to one of them, the boundary must be reclassified before deployment.

### Security reporting

GitHub Private Vulnerability Reporting is kept separate from normal customer support. Security reporters should not be asked for unnecessary user financial records or authentication secrets.

## 3. Production provider acceptance record

Before a high-risk provider is activated in production, maintain a private operator record containing non-secret facts:

- registry key;
- actual provider/service/legal name;
- feature enabled/disabled;
- region/data-center where relevant;
- categories of data actually sent;
- provider retention/deletion references and review date;
- contract/DPA/service-role review status where applicable;
- operator owner;
- date and result of the last live smoke test;
- deletion/export/revocation procedure.

Credentials stay only in deployment secret storage.

## 4. Relationship to deletion

Roadmap #10/#11 define account/workspace ownership semantics. Later executable deletion work (#29/#30) must reconcile external copies where applicable.

Deleting a SQL row locally is not sufficient when:

- a support provider retains a ticket;
- a bank/open-finance provider retains consent/session data;
- an external object store still contains uploaded bytes;
- a managed database/log service retains copies;
- an AI/provider request has provider-side retention.

Provider timeout or ambiguous response is not proof of deletion.

## 5. Change-control gate

A PR that introduces a new outbound data recipient must:

1. add a `ThirdPartyBoundary` entry;
2. classify its status and technical role;
3. list data classes and whether personal/financial/credential material can cross;
4. define deletion expectation;
5. list remaining roadmap gates;
6. keep secrets out of source;
7. add/update regression tests;
8. update this document if the human-readable inventory changes materially.

`get_third_party_boundary()` deliberately fails closed for unknown keys.

## 6. Roadmap #12 closure

#12 is engineering-complete when:

- repository-known external recipient classes are inventoried;
- selected, optional, unresolved, user-directed and internal boundaries are distinguished;
- Core Copilot's external AI upstream stays unresolved until separately accepted;
- unresolved infrastructure vendors are visible rather than fabricated;
- high-risk provider deletion/review gates are explicit;
- machine-readable tests pass in CI;
- hardening and retention docs point to the canonical registry.

#12 does **not** close hosting (#1/#2), object storage (#16), SMTP (#17), AI production acceptance (#6/#49/#50), payments (#31–#39), Privacy Policy (#27), Terms (#28), or executable deletion (#29/#30).
