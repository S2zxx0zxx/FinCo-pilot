# Legal applicability and privacy operations preparation

Review date: 2026-10-15. This is an evidence/request register, not an approved legal opinion or new public policy. Existing individual/India operator contract is a source fact, not confirmation of a person's legal identity. Do not infer addresses, company registration, age policy, regional targeting or active processors from dependencies or account access.

## Applicability register

Every row is owned by operator + qualified market counsel; independent reviewer and final review date are pending. No row is marked not applicable without substantiated facts. Exact operative deadlines need commencement/updates checked at release.

| Framework | Primary source checked / reference | Trigger and available evidence | Status / next proof |
|---|---|---|---|
| India DPDP Act / Rules | [MeitY Gazette Rules](https://www.meity.gov.in/static/uploads/2025/11/53450e6e5dc0bfa85ebd78686cadad39.pdf), Rule 1; [PIB explanatory note](https://static.pib.gov.in/WriteReadData/specificdocs/documents/2025/nov/doc20251117695301.pdf) | Rule 1 separates immediately effective rules, Rule 4 after one year, and Rules 3/5–16/22–23 after eighteen months from publication. The Gazette is dated 13 Nov 2025 with publication identifier dated 14 Nov; do not collapse this to one asserted exact operational deadline. | Needs counsel: actual fiduciary activities, Act commencement notification, publication date/corrigenda and obligation-specific deadline. Prepare notice, rights, safeguards and processor evidence now. |
| India CERT-In directions | [28 Apr 2022 primary directions](https://www.cert-in.org.in/PDF/CERT-In_Directions_70B_28.04.2022.pdf), clauses (i)–(iv), Annexure I | Covered entities/incidents have six-hour reporting from notice, PoC, time-sync and rolling 180-day secure ICT logs in Indian jurisdiction requirements. Actual operator class and sink not proven. | Needs operator/counsel scope, staffed PoC, log location/retention/clock evidence and tabletop. Do not confuse application retention constants with deployment proof. |
| India IT/SPDI / consumer / contract / tax | [MeitY acts/policies index](https://www.meity.gov.in/documents/act-and-policies) (index, not full applicability review) | Financial/personal data and subscriptions may create duties; entity/activities and continuing interaction with phased DPDP need analysis. | Needs counsel and actual offers, refunds/cancel flow, grievance and tax facts. No comprehensive legal research completion claimed. |
| EU GDPR | [Commission territorial guidance](https://commission.europa.eu/law/law-topic/data-protection/information-business-and-organisations/application-gdpr_en) | Establishment, targeting or monitoring facts matter; mere global reach is insufficient to decide scope. | Needs market facts, legal basis/purpose, processor agreements, transfer mechanism and independent review. |
| UK GDPR / DPA | [ICO transfers guidance](https://ico.org.uk/for-organisations/uk-gdpr-guidance-and-resources/international-transfers/a-guide-to-international-transfers/) | UK scope and transfers require separate analysis. | Needs actual UK market/establishment/monitoring facts and counsel; this guidance alone does not decide territorial scope. |
| California CCPA/CPRA | [CPPA monetary threshold page](https://www.cppa.ca.gov/regulations/cpi_adjustment.html) | Revenue and other statutory activity/volume tests require actual business facts; do not assume absence/presence based on website availability. | Needs revenue, covered data volumes, sale/share and California nexus; counsel validates all tests and current thresholds. |
| Brazil LGPD | [ANPD legal framework index](https://www.gov.br/anpd/pt-br/acesso-a-informacao/institucional/base-juridica) | Processing/collection/targeting territorial facts unknown. Index was checked; complete legal analysis not done. | Needs target markets, collection/processing map and Brazil counsel if in scope. |
| RBI / AA / payments / advice | [Official AA framework reference](https://www.financialservices.gov.in/account-aggregator-framework) (reference; full regulatory source review pending role facts) | Repo has bank/merchant integration support; no evidence FinCo-Pilot itself is licensed AA/FIU/FIP, aggregator, lender or adviser. | Needs exact money/data flow and partner contracts; counsel determines obligations before regulated launch claims. |
| PCI DSS | [PCI SSC standard page](https://www.pcisecuritystandards.org/standards/pci-dss/) | Outsourced card payment does not automatically eliminate merchant scope. No cardholder data collection verified. | Needs actual checkout architecture, merchant/acquirer instructions and appropriate assessor/SAQ decision. |
| SOC 2 / ISO 27001 | Blueprint optional assurance targets | No certification evidence supplied. | Optional business decision; no spend or certification claim. |

These summaries are deliberately bounded. The source blueprint's dates are not substituted for fresh legal review. No public notices, terms or regulator communications have been published or sent.

## Record of processing — provisional

Field inventory: [model schema fields](evidence/model-field-inventory.json). Source schema is not a live database inventory; classifier, purposes, legal bases and deletions require owner validation.

| Data / purpose | Source / recipients to verify | Basis and necessity | Retention / rights / gap |
|---|---|---|---|
| Identity, verified mapping, MFA/passkeys, sessions | user/external_auth_identity/passkey models; Clerk/local auth; SMTP | Necessary account/security purpose proposed; legal basis pending scope | Credential stamps/revocation and deletion tombstones; owner confirms actual identity provider and mail processor |
| Accounts, transactions, budgets, invoices, goals, assets and sharing | workspace-scoped models/API; DB and optional bank providers | User-requested finance service; confirm lawful basis and permitted shared-member visibility | Existing retention/deletion state machines; no retention job/provider receipt inferred from source |
| Connection credentials and bank consent | encrypted provider credentials, AI connections; exact bank/LLM endpoint unknown | Explicit connection/service purpose; verify scope, revocation and no secondary use | Key continuity, revoke/delete/hold/backups; live recipients and contract retention unknown |
| Uploaded statements, attachments and knowledge | import/attachment/knowledge services; private object storage / model route | Data necessary for requested import/analysis; prevent payload logs | Import logging patch; bytes/CPU quotas, storage and provider deletion need acceptance |
| AI prompts, conversations, usage and tools | Core and advanced agent stores; internal OmniRoute vs selected upstream distinct | Minimize financial context and require exact permitted tools; operator basis/provider choice pending | Do not silently approve external model route; data-retention, transfer and provider-delete facts required |
| Billing/order/subscription/refund evidence | checkout/inbox/billing models; Razorpay if enabled | Service/payment and legally required records to be classified | Server truth and dedupe tests; contracts, transaction retention and real merchant receipts pending |
| Support contact/text and diagnostics | support_service; Zoho only if configured | Requested support, minimum necessary diagnostics | Existing support-retention contract; staffed mailbox, contract, deletion tails pending |
| Security events, logs, telemetry and build artifacts | Sentry optional; actual sink unknown | Security/service purpose with minimization; applicable legal log duties assessed separately | No raw financial payloads/secrets; runtime sample, access, region, 180/365-day policy applicability and expiry proof missing |
| Backups/restore inventory | disaster recovery and recovery evidence | Availability/security with access restriction and purpose limits | Actual encrypted off-host backup, keys, RTO/RPO, isolated restore and expiry evidence pending |

## Individual-rights request runbook

1. Receive through a staffed owner-approved channel; record request ID, jurisdiction, received time, applicable clock and case owner. Never solicit passwords, OTPs or bank statements by chat/email.
2. Authenticate requester using existing account/fresh-auth mechanisms proportional to request. For inaccessible accounts use a reviewed recovery path; never grant access solely by matching a supplied email.
3. Establish personal/workspace/shared-member scope and authority. Separate another member's data, legal hold and immutable payment evidence. Log only minimum references.
4. Use scoped export/correction/deletion workflows; test with synthetic data first. Review manifest, collaborator blockers, provider revocations, external deletion requirements and backup tails before irreversible execution.
5. Give status/receipt through the authenticated case; record decisions, evidence references and refusal/extension legal basis where applicable. Owner/counsel approves substantive legal wording and deadlines.
6. Track provider follow-ups and backup expiry until receipts exist; reconcile failures and escalate. A local tombstone is not proof external copies disappeared.

## Vendor / publication / DPIA gates

For every actually LIVE recipient obtain service/legal role, contract/DPA version, subprocessors, locations/transfers, purpose/categories, retention/deletion, security contact and incident terms. Account existence does not prove that recipient handles apex data. Cloudflare edge and Vercel project metadata are connected; Neon project is Singapore; exact runtime DB binding, identity/payment/banking/SMTP/support/AI activation, Sentry sample and signed contracts remain UNKNOWN.

Risk assessment/DPIA preparation must cover financial profiling, shared-workspace exposure, optional external AI and tool approvals, children's eligibility, upload/telemetry leakage, international transfers, revocation/deletion and outage handling. Human owner supplies processing scale/markets/age facts; counsel decides mandatory DPIA/children safeguards and approves mitigations. No age gate or public policy was changed on assumptions.

Owner facts required once: legal operator identity and service address; staffed privacy/grievance and incident contact; intended countries/age eligibility; actual budgeting/advice/lending/payment activities; live provider/model list and data locations; existing contracts; subscription/refund rules and retention exceptions. Supply facts in a private approved channel, never secret values.

## License evidence, separate from privacy-law compliance

Lock-based component inventory and installed Python license metadata are recorded. npm metadata includes MIT, Apache, ISC, BSD, MPL and other licenses; nine Sentry CLI platform/dev-tool records declare FSL-1.1-MIT, so do not describe every dependency as permissive open source. Six runtime dependencies omit license metadata from the lockfile; installed LICENSE files exist (Apache headers for several, full text review still required for post-robot/zoid and any applicable notices). Counsel/release owner validates distribution, attribution and dev-tool terms. No dependencies were removed or relicensed based on metadata alone.
