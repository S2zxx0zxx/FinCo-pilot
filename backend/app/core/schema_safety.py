"""Read-only schema gates; never infer or stamp a legacy migration history."""

from collections.abc import Collection, Mapping
from functools import lru_cache
from pathlib import Path

from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import inspect, text
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import AsyncSession


class SchemaContractError(RuntimeError):
    """A database cannot safely serve this application release."""


@lru_cache(maxsize=1)
def expected_heads() -> frozenset[str]:
    backend = Path(__file__).resolve().parents[2]
    config = Config(str(backend / "alembic.ini"))
    config.set_main_option("script_location", str(backend / "alembic"))
    heads = frozenset(ScriptDirectory.from_config(config).get_heads())
    if len(heads) != 1:
        raise SchemaContractError("Application migration chain must have exactly one head")
    return heads


REQUIRED_COLUMNS: Mapping[str, frozenset[str]] = {
    "alembic_version": frozenset({"version_num"}),
    "users": frozenset({"id", "email", "hashed_password", "auth_epoch"}),
    "accounts": frozenset({"id", "user_id", "workspace_id", "balance", "currency"}),
    "transactions": frozenset({"id", "user_id", "workspace_id", "account_id", "amount", "date"}),
    "workspaces": frozenset({"id"}),
    "workspace_members": frozenset({"workspace_id", "user_id", "role"}),
    "external_auth_identities": frozenset({"id", "user_id", "issuer", "provider_subject"}),
    "checkout_reservations": frozenset({"id"}),
    "payment_webhook_events": frozenset({"id"}),
    "loans": frozenset({"id", "workspace_id"}),
}


def validate_columns(columns: Mapping[str, Collection[str]]) -> None:
    if any(not required.issubset(columns.get(table, ())) for table, required in REQUIRED_COLUMNS.items()):
        # No schema names, credentials or user/financial data in public errors.
        raise SchemaContractError("Database schema does not match this application release")


async def verify_runtime_schema(session: AsyncSession) -> None:
    rows = (await session.execute(text(
        "SELECT table_name, column_name FROM information_schema.columns "
        "WHERE table_schema = current_schema()"
    ))).all()
    columns: dict[str, set[str]] = {}
    for table, column in rows:
        columns.setdefault(table, set()).add(column)
    validate_columns(columns)
    heads = frozenset((await session.execute(text("SELECT version_num FROM alembic_version"))).scalars())
    if heads != expected_heads():
        raise SchemaContractError("Database migration head does not match this application release")


def reject_unmanaged_schema(connection: Connection, application_tables: Collection[str]) -> None:
    """Run under the migration lock, before Alembic can create or stamp tables.

    An empty version table is not proof of a baseline. Extension-only tables
    and unrelated tables do not conflict with an empty application install.
    """
    inspector = inspect(connection)
    tables = set(inspector.get_table_names())
    overlap = tables.intersection(application_tables)
    overlap.discard("alembic_version")
    if not overlap:
        return
    if "alembic_version" in tables:
        columns = {column["name"] for column in inspector.get_columns("alembic_version")}
        if "version_num" in columns:
            versions = connection.execute(text("SELECT version_num FROM alembic_version")).scalars().all()
            if versions and all(isinstance(version, str) and version.strip() for version in versions):
                return
    raise SchemaContractError(
        "Refusing unmanaged application tables: preserve the database and rehearse an explicit "
        "legacy conversion on an isolated copy. Do not stamp head or reset this database."
    )
