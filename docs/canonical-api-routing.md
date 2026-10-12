# Canonical API routing

The production frontend is https://fincopilot.app and its Axios/stream/public
invoice clients use same-origin `/api`. Its previous Vercel config correctly
excluded API paths from the SPA catch-all, but supplied no backend destination.
That returned404 before reaching the independently deployed FastAPI project.

Add the external `/api/:path*` rewrite before the retained SPA rule, targeting
https://api.fincopilot.app/api/:path*. This dedicated host is assigned to the
existing fincopilot-api project. Cloudflare's existing fincopilot.app zone gained
one new DNS-only API CNAME using the actual rank-one Vercel domain recommendation;
no apex/www/mail record or nameserver was replaced. HTTPS propagation and live
proxy behavior must be independently verified after deployment.

`/mcp` remains excluded from SPA HTML and has no invented FastAPI destination.
Its real MCP runtime and public acceptance remain separate work. API failures
must remain JSON failures; no frontend-HTML or synthetic-data success fallback.

Production API configuration is still incomplete. Until runtime/schema/provider
acceptance, liveness may return200 with application_ready=false and readiness
must return503. Working routing is not a working authenticated finance app.
