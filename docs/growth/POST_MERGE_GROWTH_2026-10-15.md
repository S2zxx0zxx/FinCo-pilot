# Growth integration after landing activation

15 October 2026. Main `ccdba0c` merges landing activation PR92 after organic-growth PR89. The established marketing namespace is now `/welcome/`, with `/dashboard` remaining protected. The earlier proposed `discover.fincopilot.app` is not a selected production host.

## Reproduced source mismatch and correction

The export uses Next's basePath `/welcome` and trailingSlash=true, but its canonical, OpenGraph, social-card and WebSite/Breadcrumb URLs were still calculated for standalone root routes. For example the actual `/welcome/features/` artifact described `/features` as its canonical, and social metadata requested `/social-card.png` rather than the exported `/welcome/social-card.png`.

This continuation makes build-time URL generation follow the selected export namespace. Standalone Next previews retain their original root-path behavior. The eligible sitemap uses the same canonical helper, and robots references the correct sitemap namespace when indexing is explicitly enabled. No indexing toggle, crawler-policy expansion, app/auth/API path, financial record or production configuration changes.

The optional IndexNow notifier accepts an explicit `--base-path /welcome` for the same four logical public routes and retains its offline default and release approval/preflight gates. The root verification key stays on the same origin; arbitrary namespaces/private/query/token paths remain rejected. No notification or key installation performed.

The discovery verifier now inspects actual static-export HTML/XML/text as well as standalone builds. CI adds a same-origin excluded export fixture. The source branch includes the current PR93 static-metadata/white-contrast corrections as a dependency; it does not modify that PR's branch or bypass its release gates.

## Required verification

- Python growth contracts and landing unit contracts, including standalone versus welcome URL/schema/social cases.
- Standalone preview, explicit-production fixture and excluded same-origin export builds; verify actual bytes and indexing flags.
- TypeScript, final diff/secret checks and relevant browser acceptance.
- The exact hosted release remains separately blocked while Vercel reports an account build-rate limit. A passed local build cannot certify a hosted deployment.

## Remaining external acceptance

Actual authorized GSC/Bing/analytics reads and consent/source definitions; completed real signup/login/checkout/activation; deployed runtime/source receipt and public/private boundary verification; truthful operator/team/contact facts; real demand/indexing/citation/cohort/resource observations; customer consent and approved distribution/publication. Scheduled review configuration alone is not a delivered report.

PR89 and PR92 are already merged. The current source ledger's historical IN PR / blocked-host descriptions must not be mistaken for current GitHub merge state. This branch is an integration continuation, not a full PDF completion certificate. Do not offer it as merge-ready while required release evidence is unavailable.

## Local verification receipt

27 Python growth tests and12 landing unit contracts passed. Landing TypeScript and three actual builds passed: excluded standalone preview (zero sitemap URLs), explicit-production standalone fixture (four URLs), excluded same-origin export (four HTML pages with welcome canonicals/social/schema; zero sitemap URLs). Final-byte discovery verifier passed each mode. Secret hygiene, workflow YAML and whitespace checks passed. These checks do not certify a hosted build while the account is rate-limited, nor real provider/customer operations.

The ledger's historical IN PR labels are now IMPLEMENTED for merged/source-built work, without changing live_verified/measured to YES. ORG007 reflects the merged welcome architecture rather than an obsolete unchosen-host proposal. PR metadata carries the latest candidate CI outcome; do not reuse earlier green checks as a new-head result.
