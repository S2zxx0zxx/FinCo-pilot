# Temporary sign-in pause — public UI preview

The production **frontend** intentionally shows a standalone public UI preview at `/` while account sign-in is paused. The login, registration, account-recovery, and protected financial pages are not mounted while paused. Direct visits to `/login` or protected routes return to the preview homepage.

**Scope:** This is a visual-only preview with blank data. It does not sign a user in, create dummy JWTs, return genuine balances, or turn off any backend authentication. Do not describe this page as an authenticated dashboard. The API's separate deployment/configuration issues are not fixed by this frontend change.

## Resume the real app later

1. In Vercel's `fincopilot-web` project, set the **Production** environment variable `VITE_LOGIN_PAUSED=false`.
2. Redeploy the frontend (Vite reads the variable at build time). Login, registration, recovery, and real protected routes are restored without modifying backend security.
3. Only resume for live users after the API is healthy, production email delivery has been configured, and the `/api` route is reaching that API. Before resuming, verify login, session, MFA, and recovery in a production-like test.

The pause defaults to **on in production builds only** unless the variable above is set to exactly `false`. Vite localhost development continues to use its existing local sign-in UI-preview behavior.

## Rollback

Revert the PR that introduced this pause, or configure `VITE_LOGIN_PAUSED=false` as above. Never make the backend return tokens for arbitrary credentials; restoring the real authentication is the intended unpause.
