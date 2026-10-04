from urllib.parse import parse_qs, urlsplit, quote
import httpx
import pytest
from app.core.config import Settings
from app.providers.s3_storage import S3StorageProvider, StorageIntegrityError
from app.providers.local_storage import LocalStorageProvider

REAL_CLIENT = httpx.AsyncClient


def settings():
    return Settings(_env_file=None, storage_provider='s3', storage_s3_bucket='synthetic-bucket', storage_s3_region='auto',
        storage_s3_endpoint_url='https://objects.example.invalid', storage_s3_access_key='synthetic-access',
        storage_s3_secret_key='synthetic-secret', storage_s3_prefix='tenant')


def xml(key, truncated='false', token=''):
    return f'<ListBucketResult xmlns="http://s3.amazonaws.com/doc/2006-03-01/"><EncodingType>url</EncodingType><IsTruncated>{truncated}</IsTruncated><Contents><Key>{quote(key, safe="")}</Key></Contents><NextContinuationToken>{token}</NextContinuationToken></ListBucketResult>'


def transport(monkeypatch, handler):
    monkeypatch.setattr('app.providers.s3_storage.get_settings', settings)
    monkeypatch.setattr('app.providers.s3_storage.httpx.AsyncClient', lambda **kw: REAL_CLIENT(**kw, transport=httpx.MockTransport(handler)))


@pytest.mark.asyncio
async def test_s3_exact_namespace_pagination_and_encoded_keys(monkeypatch):
    requests = []
    def handler(request):
        requests.append(request)
        query = parse_qs(urlsplit(str(request.url)).query)
        assert query['prefix'] == ['tenant/workspace/'] and query['encoding-type'] == ['url']
        assert request.headers['authorization'].startswith('AWS4-HMAC-SHA256 ')
        if len(requests) == 1:
            return httpx.Response(200, text=xml('tenant/workspace/logo one.png', 'true', 'opaque-token'))
        assert query['continuation-token'] == ['opaque-token']
        return httpx.Response(200, text=xml('tenant/workspace/é+two.png'))
    transport(monkeypatch, handler)
    assert await S3StorageProvider().list_keys('workspace/') == ['workspace/logo one.png', 'workspace/é+two.png']
    assert len(requests) == 2


@pytest.mark.asyncio
@pytest.mark.parametrize('payload', [
    '<!DOCTYPE root [<!ENTITY secret "bad">]><ListBucketResult/>', '<broken', '<WrongRoot/>',
    xml('tenant/other-workspace/file.png'), xml('tenant/workspace/../outside'),
    xml('tenant/workspace/file', 'true', ''), xml('tenant/workspace/file', 'maybe', ''),
    '<ListBucketResult><IsTruncated>false</IsTruncated></ListBucketResult>',
])
async def test_malformed_or_escaped_s3_inventory_fails_closed(monkeypatch, payload):
    transport(monkeypatch, lambda request: httpx.Response(200, text=payload))
    with pytest.raises(StorageIntegrityError):
        await S3StorageProvider().list_keys('workspace/')


@pytest.mark.asyncio
async def test_repeated_s3_token_and_oversized_inventory_refused(monkeypatch):
    transport(monkeypatch, lambda request: httpx.Response(200, text=xml('tenant/workspace/file', 'true', 'repeat')))
    with pytest.raises(StorageIntegrityError, match='pagination'):
        await S3StorageProvider().list_keys('workspace/')
    transport(monkeypatch, lambda request: httpx.Response(200, content=b'x'*(2*1024*1024+1)))
    with pytest.raises(StorageIntegrityError, match='exceeds limit'):
        await S3StorageProvider().list_keys('workspace/')


@pytest.mark.asyncio
async def test_local_inventory_includes_orphans_only_in_requested_workspace(monkeypatch, tmp_path):
    provider = LocalStorageProvider()
    monkeypatch.setattr(provider, '_base_path', lambda: tmp_path)
    (tmp_path/'private/invoices/logo').mkdir(parents=True)
    (tmp_path/'private/invoices/logo/old.png').write_bytes(b'old')
    (tmp_path/'shared').mkdir()
    (tmp_path/'shared/keep.pdf').write_bytes(b'keep')
    assert await provider.list_keys('private/') == ['private/invoices/logo/old.png']
    assert await provider.list_keys('missing/') == []
    (tmp_path/'private/link').symlink_to(tmp_path/'shared')
    with pytest.raises(ValueError, match='symlink'):
        await provider.list_keys('private/')
    (tmp_path/'outer-link').symlink_to(tmp_path/'shared')
    with pytest.raises(ValueError):
        await provider.list_keys('outer-link/nested/')
