"""Read-only schema/row-count inventory. Never export user rows or credentials.

Run with the intended DATABASE_URL injected through a protected environment.
This tool does not migrate, initialize, stamp, repair, or approve a cutover.
"""

import asyncio
import json

from sqlalchemy import inspect, text
from sqlalchemy.engine import Connection

from app.core.database import Base
from app.core.database_runtime import create_database_engine
from app.core.schema_safety import REQUIRED_COLUMNS, expected_heads
from app.models import *  # noqa: F403
from app.agents.models import *  # noqa: F403


def inventory(connection: Connection) -> dict:
    inspector = inspect(connection)
    tables = inspector.get_table_names()
    quote = connection.dialect.identifier_preparer.quote
    result: dict = {"read_only": True, "expected_heads": sorted(expected_heads()), "tables": {}}
    for name in sorted(tables):
        columns = inspector.get_columns(name)
        result["tables"][name] = {
            "columns": [{"name": c["name"], "type": str(c["type"]), "nullable": c["nullable"]} for c in columns],
            "row_count": connection.execute(text(f"SELECT count(*) FROM {quote(name)}")).scalar_one(),
            "primary_key": inspector.get_pk_constraint(name).get("constrained_columns", []),
            "foreign_keys": [{k: fk.get(k) for k in ("constrained_columns", "referred_schema", "referred_table", "referred_columns")} for fk in inspector.get_foreign_keys(name)],
            "indexes": [{k: idx.get(k) for k in ("name", "column_names", "unique")} for idx in inspector.get_indexes(name)],
        }
    result["missing_application_tables"] = sorted(set(Base.metadata.tables) - set(tables))
    result["missing_core_columns"] = {
        name: sorted(required - {c["name"] for c in result["tables"].get(name, {}).get("columns", [])})
        for name, required in REQUIRED_COLUMNS.items()
        if required - {c["name"] for c in result["tables"].get(name, {}).get("columns", [])}
    }
    version_columns = {c["name"] for c in result["tables"].get("alembic_version", {}).get("columns", [])}
    result["current_heads"] = (
        sorted(connection.execute(text("SELECT version_num FROM alembic_version")).scalars())
        if "version_num" in version_columns else []
    )
    return result


async def run() -> dict:
    engine = create_database_engine(short_lived=True)
    try:
        async with engine.connect() as connection:
            # All subsequent reads share one stable snapshot; PostgreSQL itself
            # rejects accidental persistent writes, even if this tool regresses.
            await connection.execute(text("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY"))
            result = await connection.run_sync(inventory)
            await connection.rollback()
            return result
    finally:
        await engine.dispose()


if __name__ == "__main__":
    try:
        report = asyncio.run(run())
    except Exception as exc:
        # Driver exceptions can contain connection or SQL parameters.
        raise SystemExit(f"Schema inventory failed ({type(exc).__name__}); inspect protected operator logs") from None
    print(json.dumps(report, indent=2, sort_keys=True))
