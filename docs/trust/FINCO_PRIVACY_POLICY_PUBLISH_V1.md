# #27 Privacy policy publication

Version: FINCO_PRIVACY_POLICY_V1_2026_10_04. Review date: 4 October 2026.

## Actual implementation

Public `/privacy` and `/api/privacy-policy` provide the same versioned English/Hindi notice without login or workspace access. Links are available from login, registration, pricing, support and the account menu. The API uses an explicit public allowlist and `Cache-Control: no-store`; the dedicated browser fetch omits credentials and auth/workspace headers. The page renders plain text, including configured identity, and includes loading, retry and draft states. Reading the notice is not blanket consent. Terms, consent records and deletion automation are separate work.

The notice follows actual account/MFA/passkey, financial/shared invoice, bank/payment/support, AI/MCP, browser storage, retention and restore behavior. It distinguishes engineering retention targets from completed deletion jobs and selected processors from active deployment facts. No guaranteed India residency, zero-risk security, operator-proof encryption, parental-consent workflow or globally complete legal compliance is asserted.

## Publication gate and deployment

Defaults deliberately expose a draft, with no effective date or invented operator contact. Enable publication only after the operator has reviewed the exact version, all active recipients and locations (including host, database, Redis, object storage, backup, email, edge, support, identity and AI), and the reachable public grievance contact. The public contact address is deliberately supplied; never populate it from private memory or secret configuration. Operator identity must be enabled and country must be IN for this reviewed notice.

Set these public environment values (Compose and Helm config support them):

| Setting | Required fact |
| --- | --- |
| OPERATOR_LEGAL_NAME | Actual public operator legal identity |
| PRIVACY_CONTACT_NAME | Responsible privacy/grievance contact |
| PRIVACY_CONTACT_EMAIL | Real monitored public mailbox |
| PRIVACY_CONTACT_ADDRESS | Appropriate actual public contact address |
| PRIVACY_PROCESSING_LOCATIONS | Reviewed actual locations and cross-border processing |
| PRIVACY_INFRASTRUCTURE_PROVIDERS | All actual infrastructure/processor recipients |
| PRIVACY_POLICY_REVIEWED_VERSION | FINCO_PRIVACY_POLICY_V1_2026_10_04 |
| PRIVACY_POLICY_EFFECTIVE_DATE | ISO date, not a future date |
| PRIVACY_POLICY_PUBLISHED | true after review |

Missing/stale/invalid declarations fail startup when publication is enabled. Config completeness is not independent legal or provider certification. Run `python -m scripts.verify_privacy_publication` from backend: it exits nonzero for incomplete/disabled publication, reporting field codes only. Never put credentials, URLs containing credentials, database strings or internal endpoints in these intentionally public values. Review substantive changes under a new version; old review tokens cannot publish a changed notice.

Verify the actual deployed HTTPS `/privacy` deep link after a refresh and `/api/privacy-policy` while logged out. Check the effective date, operator/contact accuracy, Hindi and English, reachable mailbox, privacy support link, no auth redirect, no sensitive API caching, and no secrets in the payload. Run all CI checks on the final head before merging. Publishing a git commit does not establish a live domain or operational grievance handling.

## Primary legal research

Read official notifications rather than assuming all DPDP duties have already commenced:

- MeitY G.S.R. 846(E), 13 November 2025, Digital Personal Data Protection Rules 2025: https://www.meity.gov.in/static/uploads/2025/11/53450e6e5dc0bfa85ebd78686cadad39.pdf
- MeitY G.S.R. 843(E), Act commencement phases: https://www.meity.gov.in/static/uploads/2025/11/c56ceae6c383460ca69577428d36828b.pdf
- Official WIPO Lex reproduction of India's 2011 SPDI rules, particularly privacy policy, necessity, consent, correction/withdrawal and grievance contact: https://www.wipo.int/wipolex/en/legislation/details/15063

As of this review, the principal DPDP notice/processing/rights phase is scheduled eighteen months after publication. Existing applicable SPDI/security duties and operator/entity applicability still require review. A notice does not implement consent collection, children's consent, every rights workflow or all future incident duties. Failed retrieval of additional government PDFs was not treated as verified evidence.

## Remaining real-world requirements

No VPS/domain deployment, real monitored privacy mailbox/public address, final active processor/location facts or operational publication review was supplied. Therefore the repository completes the publication mechanism and reviewed draft, not an already active production legal policy. #28 is terms publication; #29 and #30 implement personal/shared-workspace deletion. Do not label those future workflows completed or automatic erasure.
