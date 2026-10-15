# Owner action queue

Continue independent source work while these are unresolved. Do not request passwords, OTPs, private exports or production credentials in a public PR.

| ID | Prepared evidence | Smallest owner action | Impact/reversal | Status |
|---|---|---|---|---|
| APPROVAL-001 | Current topology and three options in ARCHITECTURE_DECISION.md | Choose public marketing strategy/host after reviewing proposal; no immediate DNS change | C avoids moving auth; actual release/record values require later concrete review | Decision pending |
| APPROVAL-002 | No connected GSC tools/session found | Identify existing `fincopilot.app` property in [Search Console](https://search.google.com/search-console); provide authorized connection or sanitized Performance/Pages/Sitemaps exports | Read-only report access initially; ownership verification only if missing, no account duplication | Access blocked |
| APPROVAL-003 | Bing reports unavailable | Identify existing site in [Bing Webmaster Tools](https://www.bing.com/webmasters/); authorize read access or sanitized export; import verified GSC site only if needed | No automatic publishing; revoke report access to reverse | Access blocked |
| APPROVAL-004 | Cloudflare Web Analytics records exist; GA4 presence unproved | Identify existing analytics property/consent policy and intended signup/activation definition | Read/aggregate first; tracking changes require reviewed spec, no financial event values | Access/definition pending |
| APPROVAL-005 | Apex Tunnel healthy, source/runtime unknown; dedicated API unready | Supply non-secret deployment/source receipt or authorized origin-management access; confirm current approved runtime | Do not reset DB, rotate encryption keys, bypass checks or expose env files | Origin evidence blocked |
| APPROVAL-006 | Content requires truthful operator/support/pricing facts | Confirm public business/contact facts and review final content drafts when prepared | New public claims remain unpublished; approval applies to concrete drafts | Editorial input pending |

Account setup instructions: Search Console Domain property uses DNS verification; URL-prefix has other methods. Preserve existing verified properties. Bing can import an existing verified Search Console property. Prefer existing analytics; do not add GA4 merely because a template mentions it.

Sources: [GSC property setup](https://support.google.com/webmasters/answer/34592), [ownership](https://support.google.com/webmasters/answer/9008080), [Bing verification](https://www2.bing.com/webmasters/help/add-and-verify-site-12184f8b), [GA4 web setup](https://developers.google.com/analytics/devguides/collection/ga4/web). No account creation or DNS mutation performed.
