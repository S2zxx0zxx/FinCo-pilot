from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy import create_engine, text

from app.core.schema_safety import (
    REQUIRED_COLUMNS,
    SchemaContractError,
    expected_heads,
    reject_unmanaged_schema,
    validate_columns,
    verify_runtime_schema,
)
from app.main import app


@pytest.mark.parametrize("version_table", ["absent", "empty", "invalid", "malformed"])
def test_legacy_schema_is_rejected_without_mutation(version_table):
    engine = create_engine("sqlite://")
    with engine.begin() as connection:
        connection.execute(text("CREATE TABLE users (user_id TEXT PRIMARY KEY)"))
        connection.execute(text("INSERT INTO users VALUES ('synthetic-preserved-user')"))
        if version_table == "malformed":
            connection.execute(text("CREATE TABLE alembic_version (wrong_column TEXT)"))
        elif version_table != "absent":
            connection.execute(text("CREATE TABLE alembic_version (version_num TEXT)"))
            if version_table == "invalid":
                connection.execute(text("INSERT INTO alembic_version VALUES ('')"))
        with pytest.raises(SchemaContractError, match="Do not stamp head"):
            reject_unmanaged_schema(connection, {"users", "accounts"})
        assert connection.execute(text("SELECT user_id FROM users")).scalar_one() == "synthetic-preserved-user"
    engine.dispose()


def test_fresh_install_and_managed_history_are_allowed():
    engine = create_engine("sqlite://")
    with engine.begin() as connection:
        connection.execute(text("CREATE TABLE unrelated_extension_table (id INTEGER)"))
        reject_unmanaged_schema(connection, {"users"})
        connection.execute(text("CREATE TABLE users (id TEXT)"))
        connection.execute(text("CREATE TABLE alembic_version (version_num TEXT)"))
        connection.execute(text("INSERT INTO alembic_version VALUES ('001')"))
        reject_unmanaged_schema(connection, {"users"})
    engine.dispose()


@pytest.mark.parametrize("table", list(REQUIRED_COLUMNS))
def test_missing_core_column_rejects_even_if_head_was_stamped(table):
    columns = {name: set(required) for name, required in REQUIRED_COLUMNS.items()}
    columns[table].pop()
    with pytest.raises(SchemaContractError):
        validate_columns(columns)


def test_core_contract_tracks_actual_registered_models():
    from app.core.database import Base

    for name, columns in REQUIRED_COLUMNS.items():
        if name != "alembic_version":
            assert columns.issubset(Base.metadata.tables[name].columns.keys())
    assert len(expected_heads()) == 1


@pytest.mark.parametrize("head", [None, "001", "invented"])
async def test_wrong_revision_cannot_be_runtime_ready(head):
    session = AsyncMock()
    columns = MagicMock()
    columns.all.return_value = [(table, column) for table, required in REQUIRED_COLUMNS.items() for column in required]
    revisions = MagicMock()
    revisions.scalars.return_value = [] if head is None else [head]
    session.execute.side_effect = [columns, revisions]
    with pytest.raises(SchemaContractError, match="migration head"):
        await verify_runtime_schema(session)


async def test_current_runtime_schema_passes():
    session = AsyncMock()
    columns = MagicMock()
    columns.all.return_value = [(table, column) for table, required in REQUIRED_COLUMNS.items() for column in required]
    revisions = MagicMock()
    revisions.scalars.return_value = list(expected_heads())
    session.execute.side_effect = [columns, revisions]
    await verify_runtime_schema(session)


async def test_production_readiness_returns_503_for_legacy_schema(client):
    redis = AsyncMock()
    session = AsyncMock()
    connection_test = MagicMock()
    schema = MagicMock()
    schema.all.return_value = [("users", "user_id"), ("transactions", "amount_paise")]
    session.execute.side_effect = [connection_test, schema]
    factory = MagicMock()
    factory.return_value.__aenter__ = AsyncMock(return_value=session)
    factory.return_value.__aexit__ = AsyncMock(return_value=False)
    settings = MagicMock(is_production=True, openexchangerates_app_id="", require_fx_provider=False)
    with patch("app.main.async_session_maker", factory), patch("app.main.get_redis", AsyncMock(return_value=redis)), patch("app.main.settings", settings):
        response = await client.get("/api/health/ready")
    assert response.status_code == 503
    assert response.json()["checks"]["database"] == {"ok": False, "error": "SchemaContractError"}
    assert "amount_paise" not in response.text
    assert (await client.get("/api/health/live")).status_code == 200
    assert app is not None


def test_schema_inventory_quotes_identifiers_and_exports_only_counts():
    from scripts.inspect_database_schema import inventory

    engine = create_engine("sqlite://")
    with engine.begin() as connection:
        connection.execute(text('CREATE TABLE "odd;name" (id TEXT PRIMARY KEY, note TEXT)'))
        connection.execute(text('INSERT INTO "odd;name" VALUES (:id, :note)'), {"id": "synthetic-id", "note": "synthetic-private-financial-note"})
        report = inventory(connection)
        assert report["tables"]["odd;name"]["row_count"] == 1
        assert "synthetic-private-financial-note" not in str(report)
        assert report["current_heads"] == []
    engine.dispose()
