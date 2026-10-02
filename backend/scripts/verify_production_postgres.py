"""Safe production PostgreSQL acceptance probe.

Never prints DATABASE_URL, credentials, usernames, query text containing user
data, or row contents. Production mode is read-mostly and uses only a
transaction-local temporary table for the write round-trip.
"""

from __future__ import annotations

import argparse
import asyncio
import os
from pathlib import Path

from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import text
from sqlalchemy.engine import make_url

from app.core.config import get_settings
from app.core.database_runtime import (
    create_database_engine,
    safe_database_target,
    validate_ca_file,
)


def _expected_heads() -> set[str]:
    backend_dir = Path(__file__).resolve().parents[1]
    config = Config(str(backend_dir / "alembic.ini"))
    config.set_main_option("script_location", str(backend_dir / "alembic"))
    return set(ScriptDirectory.from_config(config).get_heads())


async def _run(ci_mode: bool) -> None:
    settings = get_settings()
    url = make_url(settings.database_url)

    if ci_mode:
        if os.environ.get("FINCO_DISPOSABLE_DB_TEST") != "yes":
            raise RuntimeError("CI acceptance requires FINCO_DISPOSABLE_DB_TEST=yes")
        if url.database != "finco_ci":
            raise RuntimeError("CI acceptance is restricted to the disposable finco_ci database")
    elif not settings.is_production:
        raise RuntimeError("Production acceptance requires DEPLOYMENT_ENVIRONMENT=production")

    validate_ca_file(settings)
    engine = create_database_engine(settings, short_lived=True)

    try:
        async with engine.connect() as connection:
            server = (
                await connection.execute(
                    text(
                        """
                        SELECT
                          current_database() AS database_name,
                          current_setting('server_version_num')::int AS server_version_num,
                          pg_is_in_recovery() AS in_recovery,
                          COALESCE(
                            (SELECT ssl FROM pg_stat_ssl WHERE pid = pg_backend_pid()),
                            false
                          ) AS ssl_active
                        """
                    )
                )
            ).mappings().one()

            if int(server["server_version_num"]) < 150000:
                raise RuntimeError("FinCo-Pilot production requires PostgreSQL 15 or newer")
            if bool(server["in_recovery"]):
                raise RuntimeError("DATABASE_URL points to a read-only recovery/standby server")
            if settings.db_ssl_mode in {"require", "verify-ca", "verify-full"} and not bool(
                server["ssl_active"]
            ):
                raise RuntimeError("Database TLS is required but the active PostgreSQL session is not encrypted")

            vector = (
                await connection.execute(
                    text(
                        """
                        SELECT
                          EXISTS (
                            SELECT 1 FROM pg_available_extensions WHERE name = 'vector'
                          ) AS available,
                          EXISTS (
                            SELECT 1 FROM pg_extension WHERE extname = 'vector'
                          ) AS installed
                        """
                    )
                )
            ).mappings().one()
            if not bool(vector["available"]):
                raise RuntimeError("pgvector is not available on the production PostgreSQL server")
            if not bool(vector["installed"]):
                raise RuntimeError("pgvector is available but not installed; run Alembic migrations first")

            current_heads = {
                str(row[0])
                for row in (
                    await connection.execute(text("SELECT version_num FROM alembic_version"))
                ).all()
            }
            expected_heads = _expected_heads()
            if current_heads != expected_heads:
                raise RuntimeError(
                    "Production database migration head does not match the application release"
                )

            transaction = await connection.begin()
            try:
                await connection.execute(
                    text(
                        """
                        CREATE TEMP TABLE finco_postgres_acceptance (
                          id integer PRIMARY KEY,
                          marker text NOT NULL
                        ) ON COMMIT DROP
                        """
                    )
                )
                await connection.execute(
                    text(
                        "INSERT INTO finco_postgres_acceptance (id, marker) "
                        "VALUES (1, 'finco-postgres-acceptance')"
                    )
                )
                marker = (
                    await connection.execute(
                        text("SELECT marker FROM finco_postgres_acceptance WHERE id = 1")
                    )
                ).scalar_one()
                if marker != "finco-postgres-acceptance":
                    raise RuntimeError("Production PostgreSQL read/write round-trip failed")
            finally:
                await transaction.rollback()

            major = int(server["server_version_num"]) // 10000
            print("FinCo-Pilot PostgreSQL acceptance: PASS")
            print(f"target={safe_database_target(settings)}")
            print(f"postgres_major={major}")
            print(f"tls_active={str(bool(server['ssl_active'])).lower()}")
            print("pgvector=installed")
            print(f"alembic_head={','.join(sorted(current_heads))}")
            print("read_write_roundtrip=pass")
    finally:
        await engine.dispose()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--ci",
        action="store_true",
        help="Run only against the explicitly opted-in disposable finco_ci database.",
    )
    args = parser.parse_args()
    asyncio.run(_run(args.ci))


if __name__ == "__main__":
    main()
