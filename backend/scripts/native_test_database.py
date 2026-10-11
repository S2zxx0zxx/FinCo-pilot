"""Reject financial test-fixture writes to anything except local disposable CI."""

from collections.abc import Mapping

from sqlalchemy.engine import make_url
from sqlalchemy.exc import ArgumentError


def validate_native_test_target(database_url: str, environment: Mapping[str, str]) -> None:
    try:
        target = make_url(database_url)
    except (ArgumentError, ValueError):
        raise RuntimeError("Native financial fixtures require a valid disposable database URL") from None
    if (
        target.drivername != "postgresql+asyncpg"
        or target.host not in {"localhost", "127.0.0.1", "::1"}
        or target.database != "finco_ci"
        or target.username != "finco_ci"
        or target.query
        or environment.get("FINCO_DISPOSABLE_DB_TEST") != "yes"
        or environment.get("DEPLOYMENT_ENVIRONMENT") != "development"
        or environment.get("DATABASE_URL") != database_url
    ):
        raise RuntimeError("Native financial fixtures require the explicit local disposable finco_ci database")
