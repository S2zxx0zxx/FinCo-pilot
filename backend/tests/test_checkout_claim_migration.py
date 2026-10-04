"""Populated migration preserves legacy evidence and quarantines unknowns."""
import importlib.util
from pathlib import Path

import pytest
import sqlalchemy as sa
from alembic.migration import MigrationContext
from alembic.operations import Operations


def test_populated_claim_upgrade_preserves_records_and_refuses_loss():
    path = Path(__file__).parents[1] / 'alembic/versions/101_checkout_order_claim.py'
    spec = importlib.util.spec_from_file_location('claim_migration', path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    engine = sa.create_engine('sqlite://')
    with engine.begin() as connection:
        connection.execute(sa.text('CREATE TABLE checkout_reservations (id VARCHAR PRIMARY KEY, provider_order_id VARCHAR, status VARCHAR, reserved_at DATETIME, amount_minor INTEGER)'))
        legacy = [dict(id='0123456789abcdef0123456789abcdef', order='order_Legacy', status='verified', amount=1900),dict(id='abcdef0123456789abcdef0123456789', order=None,status='reserved',amount=9900)]
        for row in legacy:
            connection.execute(sa.text("INSERT INTO checkout_reservations VALUES (:id,:order,:status,'2026-09-01 00:00:00',:amount)"),row)
        with Operations.context(MigrationContext.configure(connection)):
            module.upgrade()
        rows = connection.execute(sa.text('SELECT * FROM checkout_reservations ORDER BY amount_minor')).mappings().all()
        assert rows[0]['provider_order_state'] == 'ready'
        assert rows[1]['provider_order_state'] == 'uncertain'
        for actual, before in zip(rows, legacy, strict=True):
            assert actual['id'] == before['id']
            assert actual['amount_minor'] == before['amount']
            assert actual['status'] == before['status']
            assert actual['provider_order_id'] == before['order']
            assert actual['provider_receipt'] == 'fp-' + str(before['id'])[:20]
            assert actual['provider_key_id'] is None
        with Operations.context(MigrationContext.configure(connection)), pytest.raises(RuntimeError, match='evidence'):
            module.downgrade()
        assert connection.scalar(sa.text('SELECT count(*) FROM checkout_reservations')) == 2
    engine.dispose()
