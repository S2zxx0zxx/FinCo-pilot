from __future__ import annotations

import ssl
from pathlib import Path
from typing import Any

from sqlalchemy.engine import URL, make_url
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.config import Settings, get_settings


_LIBPQ_SSL_QUERY_KEYS = frozenset(
    {"sslmode", "sslcert", "sslkey", "sslrootcert", "sslcrl", "channel_binding"}
)


def normalized_database_url(settings: Settings | None = None) -> URL:
    """Return an asyncpg URL without libpq-only TLS query parameters.

    Managed PostgreSQL providers commonly hand out libpq URLs containing
    sslmode/channel_binding. SQLAlchemy's asyncpg dialect passes URL query
    parameters as driver arguments, while FinCo-Pilot owns TLS explicitly via
    connect_args. Removing those keys avoids provider-specific DSN surprises and
    keeps one TLS policy for API, workers and migrations.
    """
    settings = settings or get_settings()
    url = make_url(settings.database_url)
    if url.drivername == "postgresql":
        url = url.set(drivername="postgresql+asyncpg")

    query = {key: value for key, value in url.query.items() if key not in _LIBPQ_SSL_QUERY_KEYS}
    query["prepared_statement_cache_size"] = str(settings.db_prepared_statement_cache_size)
    return url.set(query=query)


def _ssl_connect_value(settings: Settings) -> str | ssl.SSLContext | bool:
    mode = settings.db_ssl_mode
    if mode == "disable":
        return False
    if mode == "prefer":
        return "prefer"
    if mode == "require":
        return "require"

    cafile = settings.db_ssl_ca_file.strip() or None
    context = ssl.create_default_context(ssl.Purpose.SERVER_AUTH, cafile=cafile)
    if mode == "verify-ca":
        context.check_hostname = False
    return context


def database_connect_args(settings: Settings | None = None) -> dict[str, Any]:
    settings = settings or get_settings()
    return {
        "ssl": _ssl_connect_value(settings),
        "timeout": float(settings.db_connect_timeout_seconds),
        "command_timeout": float(settings.db_command_timeout_seconds),
        "server_settings": {
            "application_name": settings.db_application_name,
            "statement_timeout": str(settings.db_statement_timeout_ms),
            "idle_in_transaction_session_timeout": str(
                settings.db_idle_transaction_timeout_ms
            ),
        },
    }


def create_database_engine(
    settings: Settings | None = None,
    *,
    short_lived: bool = False,
) -> AsyncEngine:
    """Create the canonical FinCo-Pilot async PostgreSQL engine.

    API processes use the bounded QueuePool. Celery/task/migration engines are
    short-lived and use NullPool so each task cannot multiply a managed
    PostgreSQL connection budget with another hidden application pool.
    """
    settings = settings or get_settings()
    kwargs: dict[str, Any] = {
        "echo": settings.debug,
        "pool_pre_ping": True,
        "connect_args": database_connect_args(settings),
    }

    if short_lived or settings.db_pool_mode == "null":
        kwargs["poolclass"] = NullPool
    else:
        kwargs.update(
            pool_size=settings.db_pool_size,
            max_overflow=settings.db_max_overflow,
            pool_timeout=settings.db_pool_timeout_seconds,
            pool_recycle=settings.db_pool_recycle_seconds,
        )

    return create_async_engine(normalized_database_url(settings), **kwargs)


def safe_database_target(settings: Settings | None = None) -> str:
    """Return host/database metadata safe for logs and operator acceptance."""
    settings = settings or get_settings()
    url = make_url(settings.database_url)
    host = url.host or "<socket>"
    port = f":{url.port}" if url.port else ""
    database = url.database or "<unknown>"
    return f"{host}{port}/{database}"


def validate_ca_file(settings: Settings | None = None) -> None:
    """Fail clearly when a configured CA bundle path is missing."""
    settings = settings or get_settings()
    if settings.db_ssl_ca_file.strip() and not Path(settings.db_ssl_ca_file).is_file():
        raise RuntimeError("DB_SSL_CA_FILE does not exist or is not a regular file")
