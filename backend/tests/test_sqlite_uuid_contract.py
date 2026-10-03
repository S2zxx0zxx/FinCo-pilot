"""Deterministic coverage of the random-UUID SQLite fixture failure."""
import uuid

import pytest
from sqlalchemy import Column, MetaData, Table, create_engine, select, text
from sqlalchemy.dialects import postgresql
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.schema import CreateTable


def _table():
    return Table("finco_uuid_probe", MetaData(), Column("id", UUID(as_uuid=True), primary_key=True))


@pytest.mark.parametrize("value", [
    "12345678-9012-4234-8890-123456789012",
    "12345678-9012-4234-8890-12345678e123",
])
def test_sqlite_preserves_numeric_looking_uuid4_exactly(value):
    table = _table()
    target = uuid.UUID(value)
    assert target.version == 4
    engine = create_engine("sqlite:///:memory:")
    try:
        table.create(engine)
        with engine.begin() as connection:
            connection.execute(table.insert().values(id=target))
            restored = connection.execute(select(table.c.id)).scalar_one()
            assert restored == target
            assert connection.execute(text("SELECT typeof(id) FROM finco_uuid_probe")).scalar_one() == "text"
    finally:
        engine.dispose()


def test_postgres_keeps_its_native_uuid_type():
    ddl = str(CreateTable(_table()).compile(dialect=postgresql.dialect()))
    assert "id UUID" in ddl
