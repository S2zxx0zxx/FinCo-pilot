# Mobile /login Lighthouse trace — 15 October 2026

## Source and scope

- Source: user-supplied Lighthouse 13.4.1 JSON, captured at `2026-10-15T14:45:13.854Z`.
- Navigation: `https://fincopilot.app/login` (mobile Moto G Power profile, synthetic throttling).
- Repository base for this remediation: `main@ccdba0c1108e0ed29fef2447a0d956d7d1150dba`.
- This is **one production-domain synthetic lab trace**. It does not prove repeatable field performance or a deploy of any candidate fix.
- No private credentials or full network traces are published to this repository.

## Trace evidence

| Metric | Reported value |
| --- | --- |
| Performance / Accessibility / Best Practices / SEO | 42 / 100 / 100 / 100 |
| First Contentful Paint | 1,987 ms |
| Largest Contentful Paint | 10,781 ms |
| Total Blocking Time | 6,090 ms |
| Speed Index | 3,621 ms |
| Cumulative Layout Shift | 0 |
| Time to Interactive | 12,400 ms |
| Total main-thread work | 11,362 ms |
| Script evaluation / compile | 3,585 ms / 328 ms |
| Requests / scripts | 50 / 39 |
| Transferred total | ~804,438 bytes |
| Unused JavaScript opportunity | ~218 KiB (estimated) |

LCP element is a **paragraph inside the actual login form** (`Don't have an account? Create account`), not a decorative image. LCP phases: **time to first byte ~856 ms**, **element render delay ~9,926 ms**. Faster image compression is not the primary remedy for this trace. The document audit observed ~687 ms server response; CSS `/static/index-DsKCEQo1.css` (38,423 transferred bytes) was reported as render-blocking with ~1,283 ms potential delay.

The Lighthouse network dependency chain shows:
`/login` document (~1,304 ms) -> `/static/login-CT0IVEEN.js` (~2,214 ms) -> `/static/clerk-auth-adapter-45K-6VKB.js` (~7,858 ms), plus `login-clerk-RVlSZr_T.js` (~7,847 ms). These numbers represent trace *navigation-relative completion* times, not the cost of downloading just the small adapter. The Clerk browser runtime and helper chunks also consume substantial main-thread time. The largest first-party JS `index-DMO25tyO.js` cost ~1,907 ms of scripting in the bootup breakdown; its total network transfer was ~160,601 bytes. Clerk `ui-common` showed ~86,617 estimated unused bytes (not a safe signal to delete it).

The back/forward-cache audit flags `Cache-Control: no-store` on login/auth resources. **Do not change the auth/security cache policy solely to improve this audit.**

## Scoped candidate remediation (this branch)

1. Keep lazy provider loading, sign-in security boundaries, login/Google/passkey/2FA, and all existing pages intact.
2. At build time, locate real Clerk sign-in and auth adapter output chunks (only when a Clerk publishable key configures the provider).
3. Speculatively `modulepreload` them **only on `/login` and `/sign-in`**. Do not prefetch them on the landing page, unrelated guest routes or authenticated routes.
4. Bind new dynamic preload hints to the actual production `static/*.js` bytes using SHA-256 SRI, and include those hashes in strict CSP. Fail the build if configured Clerk chunks are missing or mismatched.
5. Verify these contracts in the production build guard and source tests. Preload fetches modules; it does **not** authenticate, authorize, create a session, or prefetch sensitive API data.

**Hypothesis to test, not a measured improvement:** moving the two late-discovered public chunks into the early fetch/compile window may shorten the ~5.6-second observed discovery gap and bring the login form's final paint forward on throttled mobile. It could also increase early bandwidth/CPU contention. Treat this as a controlled experiment, with the ability to revert only these hint changes.

## Still outstanding — do not mark fixed

- Confirm a real deployed, hashed production artifact on the **actual** apex origin; GitHub CI passing alone does not verify the Cloudflare Tunnel's served version.
- Compare the original 42 / 10.8s LCP / 6.09s TBT against at least 3–5 repeat Lighthouse mobile runs on the same real origin, settings and profile; inspect waterfall and p75 field LCP/INP before claiming uplift.
- Reduce first-party main-thread work and CSS-blocking cost only after measuring actual bundle composition against the already split latest-main build; avoid deleting auth or private finance functionality.
- Separate Cloudflare/host TTFB troubleshooting from JS code. Investigate origin caching of **public static assets only**, not financial APIs or sign-in documents.
- Verify real email / Google login, SSO callback, passkey and 2FA flows before merge. Keep all tenant isolation and fail-closed handling.
- Vercel preview builds may be rate-limited; the dedicated Vercel API has a separately observed configuration issue. Neither is resolved by this client-side preload change.

## Rollout gates

- Branch-only changes; no migrations, credentials, DNS, Cloudflare routing, worker activation, production deployment or merge.
- Gate: production build, existing frontend tests, desktop/mobile browser QA in Chromium/Firefox/WebKit, current JS/CSP/SRI and zero unexpected login-route regressions.
- Compare served network requests, render-critical queue length and LCP/TBT on real slow mobile profile before promoting.
- Roll back the route-specific preload hints if they increase p75 LCP/INP or compromise the provider startup; do not weaken security policy.
