# Private local QA — ORIGINAL FinCo-Pilot (not a demo UI)

This starts the existing Vite/React routes, real FastAPI application, PostgreSQL and Redis in a **separate local Docker project**. It uses the real dashboard and actual backend APIs, not a mock app or production user data.

## On the laptop running Docker Desktop

From a clone of this repository on the `feat/loopback-original-app-qa-20261012` branch:

```bash
bash scripts/qa-local-up.sh
```

Then open **http://localhost:3300/** in the browser **on the same laptop**. No FinCo-Pilot login page is needed: a server-side QA helper signs in using a dedicated QA user and the **ordinary existing** FastAPI login route. The frontend receives the ordinary authenticated session, so all existing original components, workspaces, queries, and backend authorization rules remain in place.

For subsequent runs, use the same command. It retains the QA data, because it does **not** erase Docker volumes or regenerate credentials once created.

### Security boundaries

- Docker QA runs under the separate project `finco-private-qa` with its own PostgreSQL, Redis, attachments and test account. **No production database is connected or cloned.**
- Only the frontend QA port is exposed, bound to `127.0.0.1:3300`; backend, Redis and PostgreSQL expose **no** host ports.
- Private account credentials and DB key are randomly generated to `.finco-qa.env` with file mode `0600`, ignored by Git. **Do not publish or share this file.**
- The server-side login exchange is active **only** in Vite development with `FINCO_LOCAL_QA_ENABLED=true`, the exact loopback frontend origin, and the internal Docker backend URL. It does **not** install an auth bypass or issue artificial JWTs.
- The app session still requires the real user/workspace and normal backend login/authorization. Everything under `/api` remains protected.
- `localhost` belongs to **the laptop**, not an Android phone. This setup is deliberately unavailable from phones or a public URL. To test from a phone later, use an authenticated private tunnel/network and a different secure login/session setup. **Do not** change the Docker port to `0.0.0.0` or expose the QA session endpoint to the internet.
- It is still a **development** environment; never use real bank credentials, customers, card details, or production datasets.

### When finished

```bash
docker compose --env-file .finco-qa.env -f docker-compose.qa.yml down
```

This leaves QA database and attachments intact. Do not use `down -v` unless you explicitly want to delete all QA records.

The separate Vercel QA projects are unrelated: these instructions intentionally do not require a public or cloud backend. Neither this guide nor the setup script changes `fincopilot.app`.
