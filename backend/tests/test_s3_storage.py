from urllib.parse import parse_qs, urlsplit

import httpx
import pytest

from app.core.config import Settings
from app.providers.s3_storage import S3StorageProvider, StorageIntegrityError


class _MemoryAsyncClient:
    objects: dict[str, tuple[bytes, dict[str, str]]] = {}

    def __init__(self, *args, **kwargs):
        self.timeout = kwargs.get("timeout")
        self.follow_redirects = kwargs.get("follow_redirects")

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    @staticmethod
    def _response(method: str, url: str, status: int, **kwargs) -> httpx.Response:
        return httpx.Response(
            status,
            request=httpx.Request(method, url),
            **kwargs,
        )

    async def put(self, url: str, content: bytes, headers: dict[str, str]):
        self.objects[url] = (bytes(content), {k.lower(): v for k, v in headers.items()})
        return self._response("PUT", url, 200)

    async def get(self, url: str, headers: dict[str, str]):
        entry = self.objects.get(url)
        if entry is None:
            return self._response("GET", url, 404)
        data, stored_headers = entry
        response_headers = {
            "content-type": stored_headers.get(
                "content-type", "application/octet-stream"
            ),
        }
        checksum = stored_headers.get("x-amz-meta-fincopilot-sha256")
        if checksum is not None:
            response_headers["x-amz-meta-fincopilot-sha256"] = checksum
        return self._response(
            "GET",
            url,
            200,
            content=data,
            headers=response_headers,
        )

    async def head(self, url: str, headers: dict[str, str]):
        entry = self.objects.get(url)
        if entry is None:
            return self._response("HEAD", url, 404)
        data, stored_headers = entry
        return self._response(
            "HEAD",
            url,
            200,
            headers={
                "content-length": str(len(data)),
                "content-type": stored_headers.get(
                    "content-type", "application/octet-stream"
                ),
            },
        )

    async def delete(self, url: str, headers: dict[str, str]):
        existed = url in self.objects
        self.objects.pop(url, None)
        return self._response("DELETE", url, 204 if existed else 404)


def _r2_settings(**overrides) -> Settings:
    values = {
        "storage_provider": "s3",
        "storage_s3_vendor": "cloudflare_r2",
        "storage_s3_bucket": "finco-ci-private",
        "storage_s3_region": "auto",
        "storage_s3_access_key": "synthetic-access",
        "storage_s3_secret_key": "synthetic-secret",
        "storage_s3_endpoint_url": "https://abc123.r2.cloudflarestorage.com",
        "storage_s3_prefix": "fincopilot-prod",
        "storage_s3_request_timeout_seconds": 15,
        "storage_s3_presign_ttl_seconds": 120,
    }
    values.update(overrides)
    return Settings(**values)


@pytest.fixture(autouse=True)
def _reset_memory_client():
    _MemoryAsyncClient.objects.clear()


@pytest.mark.asyncio
async def test_r2_roundtrip_uses_prefix_and_integrity_metadata(monkeypatch):
    settings = _r2_settings()
    monkeypatch.setattr("app.providers.s3_storage.get_settings", lambda: settings)
    monkeypatch.setattr("app.providers.s3_storage.httpx.AsyncClient", _MemoryAsyncClient)

    provider = S3StorageProvider()
    logical_key = "workspace/transaction/file.pdf"
    payload = b"private-financial-document"

    stored = await provider.upload(logical_key, payload, "application/pdf")
    assert stored.storage_key == logical_key
    assert stored.size == len(payload)

    assert len(_MemoryAsyncClient.objects) == 1
    url, (_, uploaded_headers) = next(iter(_MemoryAsyncClient.objects.items()))
    assert url.endswith(
        "/finco-ci-private/fincopilot-prod/workspace/transaction/file.pdf"
    )
    assert uploaded_headers["content-type"] == "application/pdf"
    assert len(uploaded_headers["x-amz-meta-fincopilot-sha256"]) == 64
    assert "synthetic-secret" not in str(uploaded_headers)

    head = await provider.verify_exists(logical_key)
    assert head.size == len(payload)
    assert await provider.download(logical_key) == payload

    await provider.delete(logical_key)
    with pytest.raises(FileNotFoundError):
        await provider.download(logical_key)


@pytest.mark.asyncio
async def test_download_rejects_checksum_mismatch(monkeypatch):
    settings = _r2_settings()
    monkeypatch.setattr("app.providers.s3_storage.get_settings", lambda: settings)
    monkeypatch.setattr("app.providers.s3_storage.httpx.AsyncClient", _MemoryAsyncClient)

    provider = S3StorageProvider()
    await provider.upload("workspace/file.pdf", b"expected", "application/pdf")

    url, (data, headers) = next(iter(_MemoryAsyncClient.objects.items()))
    headers["x-amz-meta-fincopilot-sha256"] = "0" * 64
    _MemoryAsyncClient.objects[url] = (data, headers)

    with pytest.raises(StorageIntegrityError, match="checksum"):
        await provider.download("workspace/file.pdf")


def test_presigned_url_honors_bounded_ttl(monkeypatch):
    settings = _r2_settings(storage_s3_presign_ttl_seconds=180)
    monkeypatch.setattr("app.providers.s3_storage.get_settings", lambda: settings)

    url = S3StorageProvider().get_url("workspace/report 1.pdf")
    assert url is not None
    query = parse_qs(urlsplit(url).query)
    assert query["X-Amz-Expires"] == ["180"]
    assert "X-Amz-Signature" in query
    assert "synthetic-secret" not in url


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        (
            "storage_s3_endpoint_url",
            "https://objects.example.com",
            "Cloudflare R2 endpoint",
        ),
        ("storage_s3_region", "ap-south-1", "Cloudflare R2 requires"),
        ("storage_s3_prefix", "../escape", "safe object-key prefix"),
    ],
)
def test_r2_configuration_fails_closed(field, value, message):
    with pytest.raises(ValueError, match=message):
        _r2_settings(**{field: value})
