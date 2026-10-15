# 80-control execution register

Baseline: `7736a24e7d520b9f08dd91d38e895b5d240f8a09`. All 80 controls have an individual source/test/owner/result/next-step record in [JSON](control-register.json). BLOCKED_EXTERNAL_ACCEPTANCE means the local work below does not close the complete deployed/legal control. None is a production certification. Existing test files ran in the baseline suite; scenario completeness is not inferred from file inclusion. No tasks are silently marked PASS.

| Control | Local evidence / result | External closure dependency |
|---|---|---|
| SEC-001 — Authentication route inventory | Authentication endpoints and inherited gates inventoried | Owner-controlled staged login acceptance |
| SEC-002 — Google/Clerk new user complete flow | Synthetic exchange and identity constraints exercised | Real Google signup, callback, username completion and provider outage test accounts |
| SEC-003 — Existing Clerk account re-link policy | Issuer/subject mapping reviewed |  legacy mapping must not follow email alone;Owner-reviewed existing-account mapping evidence |
| SEC-004 — Local auth coexistence switches | Coexistence switches exercised without changing configuration | Deployed switches and configured-provider acceptance |
| SEC-005 — Email verify / reset token scope | Purpose-specific audiences, reset fingerprint and locking reviewed | Real mail delivery and native concurrent reset acceptance |
| SEC-006 — JWT audience/issuer checks | App audience/stamp and provider issuer/audience paths reviewed | Independent app issuer migration decision and live provider validation |
| SEC-007 — Session revocation / expiry | Credential stamp and expiry tested locally | Provider session revocation and configured expiry evidence |
| SEC-008 — MFA challenge atomicity | Atomic challenge paths tested with mocks | Native Redis contention acceptance |
| SEC-009 — OTP replay and recovery | OTP/recovery paths exercised on synthetic users | Owner-controlled MFA/recovery device acceptance |
| SEC-010 — Passkey user-verification check | User-verification requirement and single-use challenge reviewed | Real authenticator/device acceptance |
| SEC-011 — Sensitive-action reauthentication | Fresh-auth gate exists on deletion/operator workflows | Full sensitive-operation policy and configured-provider staging acceptance |
| SEC-012 — Logout / multiple sessions | Logout revokes app sessions |  local tests passed;Cross-tab/device and upstream logout evidence |
| SEC-013 — API permission matrix | 352 OpenAPI and 353 runtime route-method entries mapped | Effective service-level policy review and staged A/B matrix |
| SEC-014 — BOLA across finance entities | Existing fixture suites exercise finance routes |  no exhaustive BOLA attestation;Native/staging two-user negative proof for every inventoried resource |
| SEC-015 — BFLA admin/user route tests | Admin and write dependency tests passed | Deployed admin denial and role acceptance |
| SEC-016 — Mass-assignment field allowlists | Typed update schemas and existing negative tests reviewed | Complete per-operation property policy review and staging tamper proof |
| SEC-017 — Cross-workspace search and export | Workspace-scoped search and export queries reviewed | Native/staged A/B search and encrypted export acceptance |
| SEC-018 — Role downgrade race tests | Membership recheck after workspace wait reviewed | Native PostgreSQL downgrade contention proof |
| SEC-019 — Workspace archive / deletion fence | Archive/deletion fences and tombstone tests passed | Native fence tests with owner-approved disposable DB |
| SEC-020 — Service-to-service trust boundaries | Separate-purpose MCP credentials and exact-action boundary reviewed | Actual internal service topology and runtime token permissions |
| SEC-021 — Tenant-bound cache keys | Request-local dashboard metadata caches reviewed |  cache audit not exhaustive;Runtime Redis/cache key inventory and cross-tenant sampling |
| SEC-022 — Object-storage access scope | Attachment ownership/provider storage tests passed | Private bucket and signed-link configured-provider acceptance |
| SEC-023 — Financial number/precision checks | Decimal finance schemas and accounting tests passed | Native precision/integrity acceptance on disposable DB |
| SEC-024 — Payment entitlement server truth | Server checkout and entitlement tests passed | Sandbox merchant/order/amount/currency acceptance |
| SEC-025 — Deployed CSP actual header | Actual apex compatibility CSP observed |  no strict-enforcement change;Provider-backed strict report-only observations and approval |
| SEC-026 — CSP report-only acceptance | Artifact-derived strict CSP support exists | No authorised staged Clerk/bank/payment CSP session |
| SEC-027 — XSS context review | React Markdown paths and absence of dangerous HTML sinks searched | Context-specific staged imported/AI content browser proof |
| SEC-028 — Third-party scripts inventory | Frontend dependency and built artifact inventory available | Actual live scripts/provider activation inventory |
| SEC-029 — CSRF / cookie transport audit | Bearer storage and explicit CORS transport reviewed | Configured cookies/subdomains and cross-site browser validation |
| SEC-030 — PostMessage + redirect origins | OAuth state and frontend message/redirect sites searched | Real redirect and popup-origin acceptance on staged hosts |
| SEC-031 — PWA confidential cache checks | PWA source excludes sensitive API caching |  Worker tests passed;Real browser offline/logout and cache sampling |
| SEC-032 — HTTPS / origin TLS posture | Apex HTTPS headers captured |  zone TLS min 1.0 and SSL full observed;Owner-approved edge changes after origin certificate/browser compatibility proof |
| SEC-033 — Cloudflare Worker cache/privacy | Seven Worker privacy tests passed |  exact live Worker artifact unknown;Deployed binding/cache rules and cross-tenant edge acceptance |
| SEC-034 — Nginx fallback /api /mcp | API/MCP fallback contracts present |  apex API is JSON 200;Exact running origin artifact and approved staged upstream failure test |
| SEC-035 — Trusted proxy hop accuracy | Right-side trusted-hop resolver reviewed | Actual proxy-hop/direct-origin topology acceptance |
| SEC-036 — Frontend bundle/source map leaks | Production build passed |  verification reports source maps absent;Complete public-bundle/CI-artifact secret candidate review |
| SEC-037 — Request/response minimization | Export scope and support minimization reviewed |  serializer audit not universal;Complete per-route response minimization and staged negative sampling |
| SEC-038 — SSRF egress audit | Configurable outbound endpoints need deployment-specific egress policy review | Owner topology/allowlist decision; approved isolated DNS-rebinding/SSRF test scope |
| SEC-039 — Safe import XML / CSV / PDF | defusedxml parser path reviewed |  import log leakage fixed with negative tests;Native parser dependency and isolated fuzz acceptance |
| SEC-040 — File decompression quotas | Knowledge size cap exists |  transaction preview reads upload without route byte cap;Owner-approved import limits and disposable resource-budget staging test |
| SEC-041 — External bank consent revocation | Synthetic revocation/provider paths tested | Real configured bank consent revoke and reconcile receipts |
| SEC-042 — Webhook HMAC and idempotency | Raw-body HMAC before durable acceptance and dedupe reviewed | Sandbox signed delivery replay and native inbox worker acceptance |
| SEC-043 — Payment cancellation/refund truth | Cancellation/refund bound state tests passed | Actual merchant cancellation/refund reconciliation evidence |
| SEC-044 — AI prompt/tool permissions | Tool and Core privacy guards exercised locally | Approved staging injection and external AI egress acceptance |
| SEC-045 — MCP exact-action approvals | Exact tool/arguments/user/workspace checks and durable approval reviewed | Native execution contention/replay and external transport acceptance |
| SEC-046 — User API abuse quotas | Redis login and plan guards tested | No live stress authorisation or accepted per-operation budget |
| SEC-047 — Redis worker queue safety | Queue/runtime configuration tests passed | Actual Redis ACL, scheduler singleton, DLQ and timeout evidence |
| SEC-048 — Errors/log redaction | Eight new privacy regression cases reproduced before patch |  focused retest required;Release approval and real telemetry redaction sample; remaining API error surfaces review |
| SEC-049 — Repository/history secret scan | Tree hygiene passed |  history 3211 UTF-8 blobs six-pattern scan found zero; entropy candidates remain;Complete candidate triage, other refs and artifact scan; actual leaked credentials require owner rotation |
| SEC-050 — CI/artifacts/env metadata scan | CI injection contract checked and build reports no maps | Private CI artifacts/env metadata access and redacted candidate review |
| SEC-051 — Real secrets owner inventory | Secret-name/consumer inventory already canonical | Actual owners, vault metadata and rotation dates must be supplied without values |
| SEC-052 — Encryption key rotation strategy | Legacy key continuity/rotation tests passed | Approved ciphertext/key continuity backup and staged provider rotation |
| SEC-053 — Database migration compatibility | Migration safety/unit contracts passed | Native PostgreSQL migration/rollback tests unavailable locally |
| SEC-054 — Database role least privilege | TLS/runtime config contracts passed |  actual SQL grants not inspected;Authorised metadata-only DB grants review; no customer rows |
| SEC-055 — Encrypted backup restore drill | Restore archive safeguards tested |  no actual backup restored;Owner-approved encrypted backup and isolated native PostgreSQL restore target |
| SEC-056 — Dependency audit + lock integrity | Frozen backend/npm installs and dated advisory scans passed with zero known reports | Repeat after dependency changes; unsupported SDK migration requires separate provider compatibility work |
| SEC-057 — GitHub Actions supply chain | Actions source review: core CI actions use full commit pins | All workflow provenance/action review and configured repository enforcement |
| SEC-058 — Branch/ruleset protection | Main branch API protected=false and rulesets response empty | Administration access/owner approval for reviewed protections |
| SEC-059 — Prod/staging provider isolation | Production configuration fail-closed tests passed | Actual production/staging provider separation and current deployed commit |
| SEC-060 — Runtime Sentry telemetry verification | Source sanitizer tests passed |  actual Sentry ingestion not queried;Owner-controlled synthetic runtime telemetry sample/access |
| SEC-061 — Operator legal identity facts | Existing contract says individual/India |  not owner fact confirmation;Owner legal name, service address and staffed grievance/privacy contact |
| SEC-062 — Public privacy publication validation | Versioned privacy publication contract tests passed | Operator facts, live processor facts and approved public policy verification |
| SEC-063 — Terms/refund/cancel assent checks | Terms/refund/cancel contracts and tests reviewed | Approved actual terms version, assent evidence and real cancellation receipt |
| SEC-064 — Data mapping + data minimization | Processing/data/retention register prepared from existing source | Owner-approved purpose/basis, field-level retention exceptions and live data flow validation |
| SEC-065 — India DPDP applicability and deadlines | Official MeitY Gazette Rules Rule 1 checked |  staged commencement, not blanket immediate scope;Counsel confirms Act commencement/corrigenda and entity applicability before exact deadline claim |
| SEC-066 — CERT-In incident/log plan | CERT-In primary directions read |  conditional clock/log operating plan prepared;Real PoC, reportability review, India log sink and retention/time-sync evidence |
| SEC-067 — GDPR / UK GDPR market applicability | Conditional EU/UK market questions and official references registered | Actual market/establishment/monitoring facts and counsel/transfer decisions |
| SEC-068 — CCPA / LGPD conditional register | CCPA revenue/other tests and LGPD territorial facts kept conditional | Revenue/volume/business model and target-region facts plus counsel |
| SEC-069 — RBI / PCI / payment role assessment | Payment source boundary reviewed |  no RBI licence or PCI scope attestation;Licensed partner/contracts, money flow diagram and merchant/PCI assessor scope decision |
| SEC-070 — Processor contracts and data locations | Canonical provider inventory preserved |  Neon account metadata proves project region, not live app binding;Actual signed contracts, region evidence and live processing list |
| SEC-071 — Rights request + deletion/provider flows | Retention-aware account/shared-workspace workflows tested locally | Real provider revocation/deletion, holds and backup-expiry receipts |
| SEC-072 — Incident playbook and legal review | Incident clocks, evidence handling and communications approval runbook drafted | Founder/legal contacts and owner/counsel tabletop signoff |
| SEC-073 — Security baseline scoreboard | Evidence scoreboard linked to exact baseline and bounded test scope | Independent release review and production acceptance |
| SEC-074 — Risk-accepted exceptions ledger | Exceptions ledger drafted with no implied risk acceptance | Owner signatures and expiry dates for each exception |
| SEC-075 — Dependabot / advisory cadence | Existing Renovate retained |  daily read-only advisory cadence configured separately;Confirm ongoing run delivery and private advisory permissions |
| SEC-076 — Security ownership and escalation | Private vulnerability channel already documented |  role accountability draft prepared;Named human incident lead/deputy and counsel contacts |
| SEC-077 — Release rollback drill | Source rollback/restore safety contracts tested | Actual last-good image and staged rollback drill with native data integrity proof |
| SEC-078 — Daily/weekly work reporting | Daily change alerts plus weekly evidence review specified | Automation creation/result and first-run delivery verification |
| SEC-079 — Monitoring budget limits | Bounded monitoring budget: no login, finance APIs, load test or retry loops | Account quota/cost observation; increase only by owner-approved budget |
| SEC-080 — Quarterly permission review | Quarterly access/restore/legal review checklist prepared | Human provider access roster, review signatures and first quarterly attestation |
