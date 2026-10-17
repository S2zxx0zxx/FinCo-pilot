from io import BytesIO
from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException, UploadFile
from pydantic import ValidationError

from app.core.config import Settings
from app.core.upload_limits import read_bounded_upload


@pytest.mark.asyncio
async def test_upload_boundary_and_untrusted_declared_size():
    file = UploadFile(BytesIO(b'12345678'), filename='statement.csv', size=1)
    assert await read_bounded_upload(file, max_bytes=8) == b'12345678'
    file = UploadFile(BytesIO(b'123456789'), filename='statement.csv', size=1)
    with pytest.raises(HTTPException) as error:
        await read_bounded_upload(file, max_bytes=8)
    assert error.value.status_code == 413


@pytest.mark.asyncio
async def test_rejected_upload_reads_only_budget_plus_one():
    file = AsyncMock(spec=UploadFile)
    file.read.return_value = b'x' * 9
    with pytest.raises(HTTPException):
        await read_bounded_upload(file, max_bytes=8)
    file.read.assert_awaited_once_with(9)


@pytest.mark.parametrize('budget', [0, -1, 101])
def test_import_budget_must_be_bounded(budget):
    with pytest.raises(ValidationError):
        Settings(_env_file=None, import_max_file_size_mb=budget)


@pytest.mark.asyncio
@pytest.mark.parametrize('path', ['/api/transactions/import/preview', '/api/assets/import/preview'])
async def test_oversized_financial_import_rejected_before_parser(client, auth_headers, monkeypatch, path):
    from app.core.config import get_settings
    from app.services import asset_import_service, import_service

    monkeypatch.setattr(get_settings(), 'import_max_file_size_mb', 1)
    parser = AsyncMock(side_effect=AssertionError('Parser must not run'))
    monkeypatch.setattr(import_service, 'parse_csv', parser)
    monkeypatch.setattr(asset_import_service, 'parse_orders_csv', parser)
    response = await client.post(path, headers=auth_headers,
        files={'file': ('statement.csv', b'x' * (1024 * 1024 + 1), 'text/csv')})
    assert response.status_code == 413
    parser.assert_not_called()
