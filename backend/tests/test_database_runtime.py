import ssl

import pytest
from sqlalchemy.pool import NullPool

from app.core.config import Settings
from app.core.database_runtime import (
    create_database_engine,
    database_connect_args,
    normalized_database_url,
    safe_database_target,
)


def _settings(**overrides):
    return Settings(
        database_url="postgresql://finco:secret@db.example.com:5432/fincopilot"
        "?sslmode=require&channel_binding=require",
        db_ssl_mode="verify-full",
        database_external_required=True,
        **overrides,
    )


def test_managed_provider_url_is_normalized_for_asyncpg_without_leaking_password():
    settings = _settings()
    url = normalized_database_url(settings)

    assert url.drivername == "postgresql+asyncpg"
    assert "sslmode" not in url.query
    assert "channel_binding" not in url.query
    assert url.query["prepared_statement_cache_size"] == "100"
    assert safe_database_target(settings) == "db.example.com:5432/fincopilot"
    assert "secret" not in safe_database_target(settings)


def test_verify_full_builds_hostname_verifying_ssl_context():
    connect_args = database_connect_args(_settings())
    context = connect_args["ssl"]

    assert isinstance(context, ssl.SSLContext)
    assert context.check_hostname is True
    assert connect_args["command_timeout"] == 30.0
    assert connect_args["server_settings"]["application_name"] == "fincopilot"


def test_short_lived_worker_engine_uses_null_pool():
    engine = create_database_engine(_settings(db_ssl_mode="disable"), short_lived=True)
    try:
        assert isinstance(engine.sync_engine.pool, NullPool)
    finally:
        # No connection was opened, so sync disposal is sufficient for this structural test.
        engine.sync_engine.dispose()


@pytest.mark.parametrize("host", ["localhost", "127.0.0.1", "db", "postgres"])
def test_external_database_gate_rejects_local_hosts(host):
    with pytest.raises(ValueError, match="external PostgreSQL"):
        _settings(
            database_url=f"postgresql+asyncpg://finco:secret@{host}:5432/fincopilot",
        )


def test_external_database_gate_requires_tls():
    with pytest.raises(ValueError, match="DB_SSL_MODE"):
        _settings(db_ssl_mode="disable")


def test_database_runtime_rejects_unknown_pool_mode():
    with pytest.raises(ValueError, match="DB_POOL_MODE"):
        _settings(db_pool_mode="mystery")
