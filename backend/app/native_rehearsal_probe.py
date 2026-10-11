"""Protected preview-only, read-only native PostgreSQL connection evidence.

This temporary branch entrypoint must never be merged or routed to production.
"""

import os
import ssl
from urllib.parse import parse_qsl, urlsplit, urlunsplit

import asyncpg
from fastapi import FastAPI
from fastapi.responses import JSONResponse

EXPECTED_HOST = "ep-summer-paper-azk614rq-pooler.c-3.ap-southeast-1.aws.neon.tech"
EXPECTED_BRANCH = "br-snowy-hill-az6xrk9v"


def validated_url(environment) -> str:
    if (environment.get("VERCEL_ENV") != "preview"
            or environment.get("FINCO_REHEARSAL_ENABLED") != "yes"
            or environment.get("FINCO_REHEARSAL_BRANCH_ID") != EXPECTED_BRANCH):
        raise ValueError("Rehearsal disabled outside isolated preview")
    value = environment.get("FINCO_REHEARSAL_DATABASE_URL", "")
    try:
        parsed = urlsplit(value)
        query = parse_qsl(parsed.query, keep_blank_values=True)
        allowed_query = {"sslmode": "require", "channel_binding": "require"}
        valid = (parsed.scheme == "postgresql" and parsed.hostname == EXPECTED_HOST
                 and parsed.path == "/neondb" and parsed.port in (None, 5432)
                 and parsed.username == "neondb_owner" and bool(parsed.password)
                 and not parsed.fragment and len(query) == len(dict(query))
                 and all(allowed_query.get(key) == value for key, value in query))
    except ValueError:
        valid = False
    if not valid:
        raise ValueError("Rehearsal target rejected")
    # Match the existing app.core.database_runtime asyncpg policy: libpq-only
    # DSN keys are removed, TLS is supplied explicitly. SCRAM channel binding is
    # not claimed by this probe; certificate/hostname verification is required.
    return urlunsplit((parsed.scheme, parsed.netloc, parsed.path, "", ""))


async def inspect_native(url: str) -> dict:
    # Verified TLS context overrides DSN sslmode; never downgrade verification.
    connection = await asyncpg.connect(url, ssl=ssl.create_default_context(),
                                      timeout=10, command_timeout=15)
    try:
        async with connection.transaction(isolation="repeatable_read", readonly=True):
            if await connection.fetchval("SHOW transaction_read_only") != "on":
                raise RuntimeError("Read-only transaction was not established")
            tables = await connection.fetch(
                "SELECT table_name FROM information_schema.tables "
                "WHERE table_schema='public' AND table_type='BASE TABLE' ORDER BY table_name"
            )
            if len(tables) > 128:
                raise RuntimeError("Unexpected rehearsal table inventory")
            counts = []
            for row in tables:
                name = row["table_name"]
                identifier = '"' + name.replace('"', '""') + '"'
                count = await connection.fetchval("SELECT count(*) FROM public." + identifier)
                counts.append({"table_name": name, "row_count": count})
            columns = await connection.fetch(
                "SELECT table_name,column_name,data_type FROM information_schema.columns "
                "WHERE table_schema='public' ORDER BY table_name,ordinal_position"
            )
            return {
                "purpose": "isolated_read_only_native_rehearsal",
                "application_ready": False,
                "read_only_enforced": True,
                "channel_binding_verified": False,
                "table_count": len(counts),
                "row_count": sum(row["row_count"] for row in counts),
                "tables": counts,
                "columns": [dict(row) for row in columns],
            }
    finally:
        await connection.close(timeout=5)


app = FastAPI(openapi_url=None, docs_url=None, redoc_url=None)


@app.get("/internal/rehearsal-evidence")
async def evidence():
    try:
        result = await inspect_native(validated_url(os.environ))
    except Exception:
        return JSONResponse(status_code=503, content={"ok": False, "application_ready": False,
                            "code": "native_rehearsal_unavailable"},
                            headers={"Cache-Control": "no-store"})
    return JSONResponse(content=result, headers={"Cache-Control": "no-store"})
