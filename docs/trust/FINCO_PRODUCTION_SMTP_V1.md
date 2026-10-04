# FinCo-Pilot roadmap #17 — production SMTP

Status: engineering implementation; live provider/sender/inbox acceptance remains gated.
Checkpoint: 2026-10-03. Branch: `feat/production-smtp-v1`.
This is the durable #17 decision record, implementation plan and continuation checklist.

## Research and decision

Keep the existing provider-neutral SMTP boundary and Python standard-library client.
No new transport dependency, database migration or queue containing raw reset tokens is
needed. Prefer verified implicit TLS (465) when supported; verified mandatory STARTTLS
(587) is also supported. Certificate/hostname validation is never disabled, TLS is at
least 1.2 and missing STARTTLS cannot fall back to plaintext.

For the current zero-budget launch, **Brevo is the recommended provider**, not a claim
that an account has been provisioned or the vendor legally approved. Its published free
allowance is 300 emails/day, with provider queuing at the limit. Resend is an alternative:
its published free allowance is 3,000/month and 100/day. These are researched limits on
2026-10-03, not an application entitlement or an unlimited-delivery promise. Brevo's free
branding/account approval and quota delays must be accepted before rollout. Production
credentials are operator-managed; the runtime stays replaceable through configuration.

Primary sources:
- [Python SMTP client](https://docs.python.org/3/library/smtplib.html)
- [IETF RFC 8314](https://www.rfc-editor.org/info/rfc8314/)
- [Brevo SMTP setup](https://help.brevo.com/hc/en-us/articles/7924908994450-Send-transactional-emails-using-Brevo-SMTP)
- [Brevo limits](https://help.brevo.com/hc/en-us/articles/208580669-FAQs-What-are-the-limits-of-the-Free-plan)
- [Brevo domain authentication](https://help.brevo.com/hc/en-us/articles/12163873383186-Authenticate-your-domain-with-Brevo-Brevo-code-DKIM-DMARC)
- [Resend SMTP](https://resend.com/docs/send-with-smtp)
- [Resend pricing](https://resend.com/pricing)

## Scanned paths and findings

`email_service.py` already used a thread, text/HTML MIME and TLS contexts. `UserManager`
already invokes it for reset/verification. The auth routers are rate-limited, local-auth
policy is preserved and reset/verification token semantics are unchanged. Production
Compose already file-mounts `smtp_password`; Helm uses its common Secret/ConfigMap.

Gaps corrected:
- Production local auth could bypass delivery-required checks; plaintext SMTP and
  incomplete auth pairs were accepted. Configuration/runtime now fail closed.
- Raw provider tracebacks could include recipient/sender/token details. Failures now
  carry only bounded reason categories; no SMTP response or message body is logged.
- Sends lacked a concurrency limit. Capacity is per process, immediate fail-closed,
  held until the actual thread finishes even if its HTTP caller is cancelled.
- SMTP acceptance and final inbox delivery were not distinguished. Success now means
  accepted by SMTP only; no automatic retry occurs after ambiguous failure.
- QUIT failure after positive DATA completion could be mistaken for failed delivery.
  Closing the connection does not overwrite a completed submission.
- Message Date/Message-ID/Auto-Submitted metadata and one explicit envelope recipient
  are added. Header/list injection is rejected; HTML URL attributes are escaped.
- Timeout/CA/capacity settings and dev/production Compose + Helm parity are explicit.

## Runtime contract

`SMTP_TIMEOUT_SECONDS=10` bounds blocking socket operations (1–60 allowed), not a
whole-transaction deadline; several protocol steps and DNS resolution can take longer.
`SMTP_MAX_CONCURRENT_SENDS=4` caps reserved sends per API process (1–16 allowed).
Multiply this by replicas/processes when budgeting provider capacity. This is not a
provider daily quota counter. Existing auth endpoint abuse limits still apply.

No background token outbox or automatic SMTP retry is introduced. SMTP cannot guarantee
exactly-once delivery: a connection loss after DATA may be ambiguous. Preserve the safe
error, check the provider dashboard and request a fresh auth email when appropriate.
A provider 250 can still be followed by a bounce, suppression, spam placement or quota
queue. Monitor provider delivered/bounced/blocked status and quota; never log message
content, links, addresses or credentials to implement that monitoring.

SMTP sees recipient addresses and **short-lived authentication links**. It receives no
financial ledger or bank credentials. Disable provider click/open tracking for these
messages where supported; tracking rewrites, provider retention and link-scanner behavior
must be reviewed. Sending a message does not verify email ownership; token consumption
does. Production outages and known/unknown-user response/timing acceptance are part of
#23/#24; this contract does not claim final anti-enumeration E2E acceptance.

## Operator setup (no secrets in chat/Git)

1. Create/activate the provider's transactional sending account; use only the free plan
   unless a paid plan is explicitly approved. Check account approval, sending limits,
   region, DPA, content/log retention, purge controls and bounce/suppression handling.
2. Choose a sender on an operator-controlled domain. `satzzxzxx.me` is available in the
   edge runbook; a dedicated sending subdomain is an option, not an invented mailbox.
   Authenticate exactly the domain used for From. Preserve existing web/mail DNS.
3. Install only the provider-returned ownership/DKIM/DMARC (and SPF/return-path if
   specifically required) records. Do not invent records, duplicate SPF/DMARC or
   overwrite existing MX. Brevo's domain-auth guide does not require blindly adding
   an SPF/MX record. Begin a compatible DMARC policy and review alignment/results.
4. Verify the sender. Retrieve SMTP login and a dedicated SMTP key; a Brevo API key
   is not its SMTP key. Set the password only in `${FINCOPILOT_SECRETS_DIR}/smtp_password`
   or the existing Kubernetes Secret's `SMTP_PASSWORD`. Revoke compromised keys and
   restart consumers after replacement.
5. Configure the actual values. Example non-secret transport shape:

```env
EMAIL_DELIVERY_REQUIRED=true
SMTP_HOST=smtp-relay.brevo.com
SMTP_PORT=465
SMTP_STARTTLS=false
SMTP_USE_SSL=true
SMTP_TIMEOUT_SECONDS=10
SMTP_MAX_CONCURRENT_SENDS=4
SMTP_SSL_CA_FILE=
# SMTP_USERNAME=<actual SMTP login from account>
# SMTP_FROM_EMAIL=<actual verified sender>
# FRONTEND_URL=https://fincopilot.satzzxzxx.me
```

For port 587 set `SMTP_STARTTLS=true`, `SMTP_USE_SSL=false`. An enterprise CA file
must be mounted read-only at the configured path. Do not disable certificate checks.
For Helm set the matching camel-case config keys and keep SMTP_PASSWORD in
`global.existingSecret`. OIDC-only production without transactional SMTP is allowed;
local-auth production must require delivery.

## Safe acceptance

From the configured production backend, test connection/TLS/AUTH/NOOP without email:

```bash
python -m scripts.verify_production_smtp
```

Then explicitly send one harmless message to an operator-controlled inbox:

```bash
python -m scripts.verify_production_smtp --send-test --recipient YOUR_CONTROLLED_INBOX
```

Do not put a password/token in the command. The probe prints neither recipient,
credentials, provider replies nor auth links. `submission=accepted` is not inbox proof.
Verify the provider delivery record, actual inbox/spam placement and Authentication-Results
for the expected DKIM/DMARC alignment. Repeat with an independent mailbox provider.
Verify the sender can receive replies or deliberately directs users to working support.
SMTP is not made a liveness/readiness dependency and the init gate never sends emails;
provider outages must not restart all finance API replicas or create acceptance-email spam.

## To-do / memory checkpoint

Engineering:
- [x] Scan auth hooks, transport, settings, abuse limits, inventory and deployment paths.
- [x] Research primary sources and record provider-neutral decision/recommendation.
- [x] Implement fail-closed TLS/auth/config, bounded sends, safe failures and metadata.
- [x] Add a safe no-send/default and explicit-send acceptance probe.
- [x] Add real local TLS SMTP regressions and deployment/secret contract tests.
- [x] Record local verification; [PR #29](https://github.com/S2zxx0zxx/FinCo-pilot/pull/29) is authoritative for final CI and merge status.

Live acceptance (not claimed complete):
- [ ] Provider account activated; actual sender/domain authenticated.
- [ ] SMTP credential installed only in secret storage; retention/region/DPA reviewed.
- [ ] Production TLS/AUTH/NOOP probe passes.
- [ ] Explicit test reaches actual controlled inboxes; provider delivery and DNS alignment verified.
- [ ] Quota, bounce/suppression, sender replies/support fallback operationally checked.
- [ ] #23 password-reset real inbox/link/login journey passes.
- [ ] #24 verification real inbox/token journey passes.

Next numbered point remains #18 FX after #17 engineering closure. #17 live acceptance
must stay visible until credentials and real evidence are available. No external account,
DNS record or email send is claimed merely because CI is green.

## Verification checkpoint

Local Python 3.12.14 locked-environment full regression: **4,155 passed, 7 skipped**,
**91.39% coverage**. The skipped reporting cases require PostgreSQL `to_char()` and
are not claimed passed. Three additional probe/inventory regressions were then added;
the focused SMTP/config/auth/security/inventory group passed **111 tests**.
CI's initial test-file type check identified two nullable MIME-body assertions; these
were corrected and the whole-backend type check and Ruff passed. The same focused
group is re-run after that correction.

Final PR-head CI, deployment validation and merge evidence are recorded in PR #29.
No real provider/inbox acceptance occurred in the local SMTP fixture: its certificates,
server, credentials and mailbox are isolated test data.


### Roadmap #23 follow-up (2026-10-04)

The forgot-password API now accepts generic requests before background lookup/SMTP,
so recipient-specific delivery failure cannot reveal registered addresses. HTTP 202
is acceptance only; configuration/capacity failures remain generic, operator SMTP
failures remain visible, and verification behavior is unchanged. Required reset
claims/single-use concurrency, notification and browser/edge protections are in
`FINCO_PASSWORD_RESET_EMAIL_E2E_V1.md`. Real inbox acceptance above remains pending.
