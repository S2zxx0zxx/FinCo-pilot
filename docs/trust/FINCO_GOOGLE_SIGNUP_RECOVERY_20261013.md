# Google signup callback recovery

## Confirmed incident evidence

User-supplied browser responses showed:
- HTTP 200 signup attempt with `status: missing_requirements`, `missing_fields: ["username"]`, and `unverified_fields: []`.
- Google external-account and email verification both `verified`; no created user or session yet.
- A separate callback-initiated `POST /v1/client/sign_ups` with `transfer: true` failed with HTTP 400 / `account_transfer_invalid`.
- Its initiator stack ran through `SSOCallbackPage`, `AuthenticateWithRedirectCallback`, and Clerk `handleRedirectCallback`.

The live callback sent incomplete signup to `/`, which is a protected financial route. `/sign-up` rendered the callback again instead of a signup-completion UI. The development frontend used StrictMode; the served Clerk React component invoked the callback from an unguarded effect. Effect replay is a confirmed code path capable of consuming an OAuth transfer twice. The error response alone does not prove the chronology of every repeated request.

## Changes

- Process the official Clerk redirect handler once per mounted callback, including StrictMode effect replay; show a safe restart notice if the callback rejects.
- Route missing signup requirements to `/sign-up#/continue`. Mount Clerk's signup UI there so required username and any future provider-configured fields are validated by Clerk.
- Explicitly configure provider login/signup destinations; keep email/password registration and its verification flow available.
- Distinguish missing required fields from an outstanding email verification in custom registration.
- Deduplicate simultaneous exchanges of the same Clerk credential. Bound login/registration session effects to one exchange attempt per provider session.
- Retain a stored credential on transient verification outages, clear private cache/user state, and block private UI. Rejected 401/403 sessions still lose their token.
- Reuse relevant frontend fixes from open draft PR #85 without carrying over its older infrastructure assumptions.

No backend models, identity mapping, database, encryption keys, Clerk requirements, Cloudflare settings, or landing-page files are modified.

## Validation and remaining acceptance

Local regression tests cover callback StrictMode replay, provider loading, rejected transfer with no secret error text, missing username, verified email, completion routing, no premature local exchange, concurrent exchange deduplication, 503 session restoration, and private-route blocking.

After merging and updating the actual Docker checkout:
1. Build/start the frontend from this commit using the project's normal compose procedure. Preserve volumes and production environment values; do not reset the database.
2. Keep Cloudflare origin stable for the entire OAuth round trip. Check `https://fincopilot.app/api/health/ready`, not just container status. Vercel API is a separate runtime and must be checked independently if used.
3. Disable artificial DevTools throttling for baseline acceptance. Test one fresh Google signup: callback -> required username screen -> completed Clerk session -> successful `/api/auth/clerk/exchange` -> `/api/users/me` -> dashboard.
4. Verify existing Google identity, email registration/verification, refresh, logout, and re-login. Existing financial users requiring approved provider-identity mapping must remain blocked; never auto-link by email.
5. Confirm no duplicate callback transfer from StrictMode and no automatic repeated exchanges on a 5xx failure. On a session verification outage, private UI must stay blocked; 401/403 must invalidate the credential.

The branch does not repair interrupted Cloudflare/origin connections. Screenshots also showed QUIC failures, 530/502 module requests, and a failed lazy import of the login page. Those are separate delivery failures. A successful build does not prove that live Google OAuth or the origin network is restored. Live acceptance remains pending until this commit is actually running in the user's Docker environment.
