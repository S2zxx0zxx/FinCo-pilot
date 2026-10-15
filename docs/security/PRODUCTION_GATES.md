# Concrete release and access decisions

No production action was executed. These requests are prepared for owner review after exact-head CI; they are not approved change orders.

| Decision / candidate change | Required preflight and acceptance | Rollback / owner dependency |
|---|---|---|
| Release diagnostic redaction and parser limits | Review import default 10 MiB (configurable 1–100); normal and limit-boundary imports; existing knowledge limits; LLM and bank retry/error categories; sanitized log sample | Revert isolated application commit / restore last-good image; no migration or data rollback |
| Release scoped collaborator directory | Default `USER_DIRECTORY_SCOPE=shared_workspaces`; self, active coworkers and explicit managers visible; unrelated/inactive/archived membership hidden; exact-email invitation lookup preserved | Revert release if legitimate collaboration regression; instance mode only with explicit trusted self-hosted privacy decision, not a silent SaaS bypass |
| Cloudflare minimum TLS 1.0 → proposed 1.2 | Confirm approved clients, payment/bank callbacks and certificate paths on staging; test all affected hostnames and TLS handshakes; observe errors | Restore recorded previous 1.0 only by explicit owner decision; no zone write performed |
| Cloudflare SSL full → consider full strict | Verify each applicable proxied origin certificate; distinguish encrypted Tunnel transport from the private HTTP hop inside the host; identify exact process/network boundary | Restore prior full setting if approved rollout fails; no blind origin/DNS changes |
| Always Use HTTPS off → proposed on | Verify existing redirect/Access/Worker routing, callback exact redirect URIs and health; avoid loops | Restore previous off setting; no public routing mutation yet |
| Strict CSP report-only trial | Identify deployed build/image and generate policy from its exact bytes; test Clerk/Google, bank, Razorpay, Sentry and PWA; observe violations with minimized reports | Return to existing compatibility mode; enforcement requires separate provider acceptance and owner release approval |
| GitHub main protection | Owner/admin confirms required CI names, reviews, bypass/maintenance rules and emergency procedure; validate with a harmless draft PR | Preserve current ruleset/branch configuration; connector administration access or owner action needed; never auto-merge |
| Outbound endpoint policy | Confirm SaaS versus trusted self-hosted advanced-agent model; enumerate approved origins/ports; include DNS rebind/redirect/IP-family handling at actual connection boundary or network firewall | Preserve intentional local Ollama/LM Studio functionality; no ineffective DNS-only allowlist or unreviewed blanket private-network block |
| Import resource isolation | Set ingress total body and multipart spool/disk/concurrency budgets, parser byte/CPU/time/decompression limits and async worker queues from an isolated benchmark | Adjust configurable budgets with measured false-positive review; no live load testing authorized |
| Real provider and data recovery acceptance | Owner-controlled staging Google/Clerk/MFA/passkey/mail/bank/payment accounts; exact upstreams; actual encrypted backup, legacy keys, isolated target and approved restore scope | No production customer data copied, credentials requested in chat, production key replacement, live refund or deletion |
| Legal/publication | Actual operator, staffed contacts, country/age/product role, active processors/regions/contracts, assent/refund facts and counsel conclusions | No fabricated names/addresses/licenses, public legal notices or regulator messages |

Exact-email lookup remains a deliberate invite-discovery surface. Its rate/abuse policy and whether invitations should become blind/non-enumerating require a separate product/privacy decision; narrowing the bulk directory does not make that residual behavior disappear.

PostgreSQL/Redis CI uses disposable fixtures and synthetic encrypted backup/restore. It does not certify the actual Neon grants, live backup, India log residency, real bank revocation or user-facing provider delivery.
