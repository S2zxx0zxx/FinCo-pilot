# Temporary local demo login (development only)

This is an **opt-in, disposable local development** convenience. The normal
production login/2FA/passkey flows stay intact. Enabling it allows any
**non-empty username and password** on the normal login form, but signs the
browser into a separate, non-admin `finco-temporary-demo@example.com` account,
**not** the account named by the supplied username. Only the demo account's
newly created personal workspace and data can be accessed.

## Enable on your own computer

1. Make a **separate empty local PostgreSQL database** for the demo. Do not
   point at production, staging, a replicated customer database, or a database
   containing actual private financial records.
2. In the backend's **local** `.env`, set:
   ```dotenv
   DEPLOYMENT_ENVIRONMENT=development
   LOCAL_AUTH_ENABLED=true
   FRONTEND_URL=http://localhost:5173
   DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/fincopilot_demo
   TEMPORARY_DEMO_LOGIN_ENABLED=true
   ```
   The local database must exist and be migrated using the repository's normal
   development database setup. Keep these values out of deployed environments.
3. Restart the **backend**, then open the Vite frontend at
   `http://localhost:5173/login` on this computer. Fill both login fields with
   any non-empty text and submit. For example: `hello` / `hello`.
4. The normal JWT and workspace controls still apply. The first demo sign-in
   creates the isolated demo user, default workspace, categories and wallet.
   A clear notice appears on the login page only while the server advertises
   the local demo setting.

Both the backend database hostname and the frontend origin must be loopback
(`localhost`, `127.0.0.1`, or `::1`), and the browser must send the exact
configured local `Origin`. Arbitrary-credential demo sign-in is disabled by
default and fails config validation in staging/production/test or on remote
database/frontend hosts. Requests without the allowed origin use the normal
credential flow.

This is **not** a way to access the owner's existing financial data or to
test production identity integration. No hard-coded shared password is created,
and no real account's password or second factor is bypassed.

## Disable immediately after testing

Set `TEMPORARY_DEMO_LOGIN_ENABLED=false` (or remove the variable) and
restart the backend. **Previously issued demo JWTs will stop validating**
even before expiration, because this mode has an additional session gate.
Normal account authentication is unaffected. You can delete the separate
development database when finished.

Never merge this as a default-on production feature, and never use it with
production credentials, realistic customer datasets, or public hosting.
