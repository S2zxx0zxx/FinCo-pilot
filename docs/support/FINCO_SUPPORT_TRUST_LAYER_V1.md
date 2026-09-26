# FinCopilot Support & Trust Layer V1

Status: implementation contract for roadmap **#7 — Support email / support channel**.

This document defines the production behavior of the customer-support surface. It does **not** claim that a real support inbox is operational until the operator acceptance checklist at the end passes.

## 1. Goals

A user who is blocked anywhere in FinCopilot must have a private, actionable path to support without being asked to send financial records or authentication secrets.

V1 provides:

- a public `/support` route reachable before login;
- public non-secret support discovery at `GET /api/support/info`;
- an authenticated structured ticket endpoint at `POST /api/support/tickets`;
- safe diagnostic context and opaque request correlation IDs;
- customer-support routing that prioritizes severity before commercial plan;
- explicit separation of customer support, transactional email, and security reporting;
- provider-neutral email/portal fallback;
- an optional Zoho Desk adapter for direct ticket creation;
- Docker Compose and Helm configuration parity;
- fail-closed provider configuration and bounded direct-submission rate limiting.

## 2. Trust boundaries

These are separate systems and must remain separate:

| Purpose | Channel |
| --- | --- |
| Customer/account/product/billing support | FinCopilot Help & Support → configured support inbox/portal/helpdesk |
| Password reset and verification email | transactional SMTP (`SMTP_*`) |
| Vulnerability reports | GitHub Private Vulnerability Reporting / configured `SUPPORT_SECURITY_URL` |

Do not tell users to send vulnerabilities through normal customer support. Do not use a social-media DM as the official channel for account, billing, privacy, or financial-data issues.

## 3. Data sent with a direct ticket

The server owns identity and entitlement context. The browser may send only bounded diagnostic hints.

Allowed diagnostic context:

- FinCopilot support reference;
- server request reference;
- authenticated user ID;
- effective plan and support tier;
- issue category and derived severity;
- app-relative page path with query string and fragment removed;
- app version;
- locale;
- prior opaque request reference;
- bounded User-Agent string.

The implementation does **not** automatically attach balances, transactions, statements, bank credentials, payment-card data, chat history, provider API keys, access tokens, refresh tokens, passwords, OTPs, PINs or CVV/CVC values.

High-confidence credential patterns in the user-entered subject/message are rejected before provider delivery. The UI also warns users not to send secrets.

## 4. Routing contract

Severity is evaluated before plan tier.

High-severity categories:

- account access;
- billing/payment;
- Safe-to-Spend / money-integrity;
- privacy/data requests.

Normal severity:

- bank connection/sync;
- transactions/import;
- FinCo Copilot;
- bug/performance;
- other.

Low severity:

- feature requests.

Commercial support tiers remain:

- Free → Standard;
- Pro → Priority;
- Max → Highest priority.

A Free user's high-severity account/privacy/money issue must not sit behind a Max user's feature request. Plan tier is used only within lower-severity work.

Do not advertise guaranteed response-time SLAs until the operator can consistently meet them.

## 5. Request correlation

Every backend request receives a server-generated opaque reference:

`FCREQ-XXXXXXXXXXXX`

The response exposes it in `X-Request-ID`. In production, unhandled server errors return the same opaque ID in a sanitized JSON response and log the ID server-side. Development/test keeps native exception propagation for debugging and regression tests.

The frontend remembers request IDs from failed API responses only. Successful background requests must not overwrite the last actionable error reference.

Direct support tickets receive a separate support reference:

`FC-XXXXXXXXXX`

This lets an operator connect the ticket to backend diagnostics without exposing exception strings or financial records.

## 6. Configuration

### 6.1 Contact-only mode

Use this mode first if a real support inbox/portal exists but direct helpdesk API credentials are not ready.

```env
SUPPORT_ENABLED=true
SUPPORT_EMAIL=<real support inbox>
SUPPORT_PORTAL_URL=<optional real portal URL>
SUPPORT_HELP_CENTER_URL=<optional real help-center URL>
SUPPORT_SECURITY_URL=https://github.com/S2zxx0zxx/FinCo-pilot/security/advisories/new
SUPPORT_PROVIDER=external
SUPPORT_TICKET_SUBMISSION_ENABLED=false
```

At least `SUPPORT_EMAIL` or `SUPPORT_PORTAL_URL` is required when support is enabled.

### 6.2 Zoho Desk direct-ticket mode

FinCopilot currently defaults the Zoho endpoints to the India data center:

```env
ZOHO_DESK_ACCOUNTS_DOMAIN=https://accounts.zoho.in
ZOHO_DESK_API_DOMAIN=https://desk.zoho.in
```

The backend accepts only an explicit allowlist of documented Zoho Desk data-center origins and requires the Accounts and Desk endpoints to match the same configured region.

Set the non-secret values:

```env
SUPPORT_ENABLED=true
SUPPORT_EMAIL=<real support address>
SUPPORT_PORTAL_URL=<real portal URL if available>
SUPPORT_HELP_CENTER_URL=<real help-center URL if available>
SUPPORT_PROVIDER=zoho_desk
SUPPORT_TICKET_SUBMISSION_ENABLED=true
SUPPORT_RATE_LIMIT_PER_HOUR=6

ZOHO_DESK_ORG_ID=<organization id>
ZOHO_DESK_DEPARTMENT_ID=<department id>
ZOHO_DESK_CLIENT_ID=<oauth client id>
```

Store these **only** in deployment secret storage:

```env
ZOHO_DESK_CLIENT_SECRET=<secret>
ZOHO_DESK_REFRESH_TOKEN=<secret>
```

Never commit them, paste them into documentation, ship them to the frontend, or put them in `VITE_*` variables.

The OAuth client should use the minimum current Zoho Desk permission needed for ticket creation (currently `Desk.tickets.CREATE`). Re-check Zoho's official OAuth documentation when provisioning because provider requirements can change.

## 7. Kubernetes / Helm

The chart's common ConfigMap renders all non-secret `.Values.config` keys into uppercase environment variables. The common Secret renders `.Values.secret` values.

For production, prefer `global.existingSecret` rather than embedding secrets in a committed values file.

Support configuration is consumed by the backend, migration job, and other workloads that inherit the common environment. Only the backend exposes the support API.

## 8. Helpdesk content safety

Zoho Desk ticket descriptions are HTML-capable. FinCopilot HTML-escapes the full generated description before preserving line breaks. Requester-controlled content must never be inserted as raw markup.

Provider failures:

- do not log access tokens or provider response bodies;
- do not automatically retry ticket creation, because an uncertain first attempt could create duplicates;
- return a safe error and an opaque FinCopilot reference;
- leave email/portal fallback visible to the user.

## 9. Abuse controls

Direct ticket creation:

- requires an authenticated active user;
- resolves plan server-side;
- is bounded by a Redis-backed per-user UTC-hour counter;
- fails closed when the direct provider is not fully configured.

The public support-info endpoint contains only non-secret destinations and capability flags.

## 10. Zero-cost launch position

Roadmap #7 can be operated without buying a FinCopilot custom domain by using the real default support address/portal provided by the selected helpdesk account.

A custom `support@<FinCopilot-domain>` address is a later branding/deployment improvement and is not required for the V1 architecture.

This does not close roadmap #17. Transactional email delivery for password-reset/verification is a separate production acceptance item.

## 11. Processor / retention dependency

When Zoho Desk is enabled with real users, it becomes part of FinCopilot's third-party support-processing inventory. Roadmap #9 (retention) and #12 (processor inventory) must define:

- what support data is retained;
- deletion/export procedures;
- the applicable provider/data-center setup;
- who can access tickets;
- retention duration and operator deletion procedure.

Do not claim those roadmap items are complete merely because this support integration exists.

## 12. Production acceptance checklist

Roadmap #7 may be marked **DONE** only when every item below passes against the real configured support account:

1. A real support inbox or portal exists and can be accessed by the operator.
2. `SUPPORT_ENABLED=true` exposes the correct non-secret destination at `/api/support/info`.
3. Logged-out users can reach Help & Support from authentication/recovery surfaces.
4. Logged-in users can reach Help & Support from the global user menu.
5. Payment-verification failures can open support with the billing category and request reference.
6. In production, a controlled backend 5xx returns an `X-Request-ID` and the same ID appears in server logs.
7. A real direct test ticket reaches the intended Zoho Desk department when direct submission is enabled.
8. The ticket contains the correct category, plan-derived support tier and safe diagnostics.
9. A test password/token-like secret is rejected before provider delivery.
10. No OAuth/client secret appears in `GET /api/info`, `GET /api/support/info`, frontend bundles, logs, screenshots or committed files.
11. A provider outage gives the user a safe fallback and does not create an automatic retry storm.
12. Security-vulnerability reporting opens the private security channel, not the customer-support queue.
13. Docker Compose configuration validates.
14. Helm lint/render validation passes.
15. Backend and frontend automated tests, type checking, build and lint pass in CI.

Until items 1 and 7 are tested with the real external account, the implementation is **code-complete but operational acceptance remains pending**.
