from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app import native_rehearsal_probe as probe


@pytest.fixture
def environment():
    return {
        "VERCEL_ENV": "preview", "FINCO_REHEARSAL_ENABLED": "yes",
        "FINCO_REHEARSAL_BRANCH_ID": probe.EXPECTED_BRANCH,
        "FINCO_REHEARSAL_DATABASE_URL": f"postgresql://neondb_owner:synthetic@{probe.EXPECTED_HOST}/neondb?sslmode=require",
    }


def test_exact_isolated_preview_target_is_accepted(environment):
    assert probe.validated_url(environment) == environment["FINCO_REHEARSAL_DATABASE_URL"].split("?")[0]


@pytest.mark.parametrize("query", ["sslmode=disable", "sslmode=prefer", "host=production.neon.tech",
                                  "sslmode=require&sslmode=disable", "options=anything"])
def test_query_cannot_override_target_or_tls(environment, query):
    environment["FINCO_REHEARSAL_DATABASE_URL"] = environment["FINCO_REHEARSAL_DATABASE_URL"].split("?")[0] + "?" + query
    with pytest.raises(ValueError):
        probe.validated_url(environment)


@pytest.mark.parametrize("field,value", [
    ("VERCEL_ENV", "production"), ("VERCEL_ENV", "development"),
    ("FINCO_REHEARSAL_ENABLED", "no"), ("FINCO_REHEARSAL_BRANCH_ID", "production-branch"),
    ("FINCO_REHEARSAL_DATABASE_URL", "postgresql://owner:secret@localhost/neondb"),
    ("FINCO_REHEARSAL_DATABASE_URL", "postgresql://owner:secret@production.neon.tech/neondb"),
    ("FINCO_REHEARSAL_DATABASE_URL", "not-a-url"),
])
def test_other_targets_and_environments_fail_closed(environment, field, value):
    environment[field] = value
    with pytest.raises(ValueError):
        probe.validated_url(environment)


def connection(readonly="on"):
    conn = AsyncMock()
    transaction = MagicMock()
    transaction.__aenter__ = AsyncMock()
    transaction.__aexit__ = AsyncMock(return_value=False)
    conn.transaction = MagicMock(return_value=transaction)
    conn.fetchval.side_effect = [readonly, 3]
    conn.fetch.side_effect = [[{"table_name": 'odd";table'}], [
        {"table_name": 'odd";table', "column_name": "id", "data_type": "uuid"},
    ]]
    return conn


async def test_native_probe_enforces_read_only_quotes_tables_and_closes(environment):
    conn = connection()
    with patch.object(probe.asyncpg, "connect", AsyncMock(return_value=conn)) as connect:
        result = await probe.inspect_native(probe.validated_url(environment))
    conn.transaction.assert_called_once_with(isolation="repeatable_read", readonly=True)
    conn.fetchval.assert_any_call('SELECT count(*) FROM public."odd"";table"')
    conn.close.assert_awaited_once_with(timeout=5)
    assert connect.call_args.kwargs["ssl"].check_hostname is True
    assert result["read_only_enforced"] is True
    assert result["application_ready"] is False
    assert result["row_count"] == 3


async def test_no_catalogue_reads_without_read_only_transaction(environment):
    conn = connection(readonly="off")
    with patch.object(probe.asyncpg, "connect", AsyncMock(return_value=conn)):
        with pytest.raises(RuntimeError):
            await probe.inspect_native(probe.validated_url(environment))
    conn.fetch.assert_not_awaited()
    conn.close.assert_awaited_once()
