# FinCo-Pilot OmniRoute Gateway

This directory is the production-oriented OmniRoute deployment boundary for FinCo-Pilot.

## Why it is separate

FinCo-Pilot must never depend on a browser-to-model connection. The supported path is:

```text
FinCo-Pilot browser
        |
        v
FinCo-Pilot backend
        |
        | OpenAI-compatible HTTPS (/v1)
        v
Dedicated OmniRoute VPS
        |
        v
Approved free-provider/model pool
```

OmniRoute is a gateway, not the source of truth for financial calculations. FinCo-Pilot's deterministic services/tools remain responsible for balances, totals, dates, budgets, forecasting inputs, and other financial arithmetic. The LLM explains and converses over validated tool outputs.

## Version policy

The canonical upstream project is `diegosouzapw/OmniRoute`.

This deployment pins `diegosouzapw/omniroute:3.8.50` rather than `latest`, `next`, or a moving branch. Upgrade only as an explicit change after reading upstream changes and running the smoke test.

Do not silently switch to a floating image tag on launch day.

## Zero-spend rule

**Do not treat OmniRoute's headline free-token number as a guaranteed allowance or SLA.** Free tiers, quotas, and provider terms change.

For FinCo-Pilot's initial zero-investment phase:

1. Use a dedicated OmniRoute instance for FinCo-Pilot.
2. Do not add paid API keys, paid subscriptions, or provider accounts that can incur usage charges to this instance.
3. Create a persisted OmniRoute combo named **`fincopilot-free-smart`**.
4. Put only provider/model targets you have explicitly reviewed and accepted into that combo.
5. Keep FinCo-Pilot configured to request exactly `fincopilot-free-smart`.
6. If every approved free target is unavailable, the request should fail gracefully. It must **not** spend money by silently falling through to a paid target.

Do not use broad `auto` / `auto/smart` as the production FinCo model when the OmniRoute instance also contains paid connections. OmniRoute's automatic routing is intentionally broad. A dedicated persisted combo gives FinCo-Pilot an explicit routing boundary.

Also note that OmniRoute's `:free` auto-tier filtering is documented as fail-open when no matching candidate is found; that behavior is useful for general routing but is not a hard zero-spend guarantee. The explicit FinCo combo plus a free-only dedicated instance is the safer boundary.

## Privacy rule

Free does not automatically mean suitable for personal financial data.

Before adding a provider to `fincopilot-free-smart`, review its current terms, retention/training policy, geographic/data-processing implications, rate limits, and tool-calling quality. FinCo-Pilot should send the minimum context required. Account numbers, credentials, access tokens, provider secrets, and unrelated raw transaction history must never be placed in the prompt.

The AI remains read-only for launch. Any future mutation must go through FinCo-Pilot's existing proposal/confirmation workflow, never direct database access from OmniRoute.

## 1. VPS prerequisites

Recommended baseline:

- Linux VPS
- Docker Engine + Compose v2
- Caddy (or another TLS reverse proxy)
- DNS record for a dedicated API hostname, e.g. `ai.example.com`
- firewall allowing only SSH, HTTP and HTTPS from the internet

Do not expose Redis. Do not expose OmniRoute's dashboard port publicly.

## 2. Create secrets

```bash
cd deploy/omniroute
cp .env.example .env

openssl rand -base64 48
openssl rand -hex 32
openssl rand -hex 32
openssl rand -hex 32
```

Put the generated values into `.env` as `JWT_SECRET`, `API_KEY_SECRET`, `STORAGE_ENCRYPTION_KEY`, and `OMNIROUTE_WS_BRIDGE_SECRET`. Generate a separate strong `INITIAL_PASSWORD`.

Never commit `.env`.

## 3. Start OmniRoute

```bash
docker compose pull
docker compose up -d
docker compose ps
```

The compose stack binds both ports to host loopback:

- dashboard: `127.0.0.1:20128`
- inference API: `127.0.0.1:20129`

Redis is not published.

## 4. Open the dashboard safely

From your own machine:

```bash
ssh -L 20128:127.0.0.1:20128 root@YOUR_VPS_IP
```

Then open `http://127.0.0.1:20128` locally.

Log in with `INITIAL_PASSWORD`, change the password, and configure only approved free providers.

Create **two different credentials** while bootstrapping:

- a short-lived or ops-only API key with OmniRoute's `manage` scope, used only to create/verify the FinCo combo;
- a dedicated FinCo-Pilot inference API key with the minimum client/inference permission the UI supports.

The FinCo application key must not have management access. Revoke the temporary management key after bootstrap unless you intentionally retain it in an operations secret store.

## 5. Build the FinCo free-only combo

After you have tested and approved the exact free model routes, bootstrap the persisted combo from the VPS:

```bash
export OMNIROUTE_MANAGEMENT_URL="http://127.0.0.1:20128"
export OMNIROUTE_MANAGEMENT_KEY="<manage-scoped bootstrap key>"
export FINCO_FREE_MODELS="provider-a/model-x,provider-b/model-y"

sh ./bootstrap-free-combo.sh
# The script re-reads the persisted combo and verifies the boundary itself.

unset OMNIROUTE_MANAGEMENT_KEY
```

The script first enables OmniRoute's global `freeAccessPolicy=strict` and `excludeTosAvoid=true`, validates every declared model against the instance's current free-tier catalog, then creates `fincopilot-free-smart` with:

- only the fully-qualified model routes you supplied;
- `allowedProviders` restricted to those providers;
- the auto router's candidate pool restricted to those providers;
- health checks and routing metrics enabled;
- no automatic mutation of an existing mismatched combo.

If an existing combo differs from the declared provider/model policy, the script **fails closed** and requires human review instead of broadening the pool.

Prefer models that have reliable tool/function calling, because FinCo-Pilot's assistant retrieves user data through tools rather than inventing financial facts.

Do not add a target merely because it is labeled "free" in a catalog. Verify the live provider terms, privacy/retention policy, rate limits, and current free allowance first. The mandatory admission rules are documented in [`PROVIDER_POLICY.md`](./PROVIDER_POLICY.md).

## 6. Publish only the API plane over TLS

Install Caddy on the host, copy `Caddyfile.example`, replace the hostname, and point DNS to the VPS.

Caddy proxies the public hostname to `127.0.0.1:20129`. The management dashboard stays local-only on port 20128.

OmniRoute inference authentication remains enabled with `REQUIRE_API_KEY=true`; TLS is not a replacement for the API key.

## 7. Run a real smoke test

From a trusted machine:

```bash
export OMNIROUTE_URL="https://ai.example.com/v1"
export OMNIROUTE_API_KEY="<dedicated FinCo key>"
export OMNIROUTE_MODEL="fincopilot-free-smart"

sh ./smoke-test.sh
```

The test fails if the dedicated combo is absent, then sends a real authenticated LLM request through OmniRoute.

## 8. Connect FinCo-Pilot

FinCo-Pilot already has a tested OpenAI-compatible provider abstraction. No GPT dependency is required; `openai_compatible` is only the protocol adapter.

Set the FinCo-Pilot backend environment:

```env
AGENTS_ENABLED=true
AGENTS_DEFAULT_PROVIDER=openai_compatible
AGENTS_DEFAULT_MODEL=fincopilot-free-smart
AGENTS_OPENAI_COMPAT_BASE_URL=https://ai.example.com/v1
AGENTS_OPENAI_COMPAT_API_KEY=<dedicated FinCo key>
```

Keep embeddings on FinCo's native local provider initially:

```env
AGENTS_EMBEDDING_PROVIDER=native
```

That avoids spending external inference quota on knowledge-base embeddings.

## 9. Failure behavior

For launch:

- provider quota/rate limit → OmniRoute may try another target inside the explicit FinCo combo;
- every approved target unavailable → return a temporary AI-unavailable state;
- core FinCo pages, balances and calculations must continue working;
- never change the model to a paid target as an emergency fallback;
- never retry indefinitely.

## 10. Relationship with PR #7

This OmniRoute work lives on `feat/ai-omniroute-gateway-v1`, created from the current `main` SHA before PR #7 is merged.

PR #7 remains independent. Before the OmniRoute PR is merged:

1. finish/merge PR #7;
2. update/rebase the OmniRoute branch onto the new `main`;
3. resolve any config conflicts deliberately;
4. run the full CI suite;
5. only then merge the AI PR.

This directory intentionally does not modify `docker-compose.prod.yml` yet because PR #7 already changes that file.
