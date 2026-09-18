import hashlib
import hmac
from datetime import datetime, timezone
from urllib.parse import parse_qsl, quote, urlsplit, urlunsplit

import httpx

from app.core.config import get_settings
from app.providers.storage import StorageProvider, StoredFile


_ALGORITHM = "AWS4-HMAC-SHA256"
_SERVICE = "s3"


def _sha256_hex(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _hmac(key: bytes, value: str) -> bytes:
    return hmac.new(key, value.encode("utf-8"), hashlib.sha256).digest()


def _canonical_query(params: list[tuple[str, str]]) -> str:
    # SigV4 requires RFC3986 encoding and byte-order sorting after encoding.
    encoded = [
        (quote(str(k), safe="-_.~"), quote(str(v), safe="-_.~")) for k, v in params
    ]
    encoded.sort()
    return "&".join(f"{k}={v}" for k, v in encoded)


def _canonical_uri(path: str) -> str:
    # S3 does not normalize paths. Preserve '/' while RFC3986-encoding each key.
    return quote(path or "/", safe="/-_.~")


class S3StorageProvider(StorageProvider):
    """S3-compatible attachment storage using the repo's existing HTTP stack.

    This implementation deliberately avoids adding an AWS SDK dependency, so
    the frozen ``uv.lock`` remains deterministic. Requests use AWS Signature V4
    and work with AWS S3 plus path-style S3-compatible endpoints such as R2 or
    MinIO when ``STORAGE_S3_ENDPOINT_URL`` is configured.

    Production deployments should use a bucket with server-side encryption,
    versioning and lifecycle/retention configured at the storage-provider level.
    """

    @property
    def name(self) -> str:
        return "s3"

    @staticmethod
    def _settings():
        settings = get_settings()
        if not settings.storage_s3_bucket.strip():
            raise RuntimeError("STORAGE_S3_BUCKET is required when STORAGE_PROVIDER=s3")
        if not settings.storage_s3_region.strip():
            raise RuntimeError("STORAGE_S3_REGION is required when STORAGE_PROVIDER=s3")
        if not settings.storage_s3_access_key.get_secret_value().strip():
            raise RuntimeError("STORAGE_S3_ACCESS_KEY is required when STORAGE_PROVIDER=s3")
        if not settings.storage_s3_secret_key.get_secret_value().strip():
            raise RuntimeError("STORAGE_S3_SECRET_KEY is required when STORAGE_PROVIDER=s3")
        return settings

    @staticmethod
    def _validate_key(storage_key: str) -> str:
        key = storage_key.strip().lstrip("/")
        if not key or key == ".." or key.startswith("../") or "/../" in f"/{key}/":
            raise ValueError("Invalid storage key")
        return key

    @classmethod
    def _object_url(cls, key: str) -> str:
        settings = cls._settings()
        bucket = settings.storage_s3_bucket.strip()
        endpoint = settings.storage_s3_endpoint_url.strip().rstrip("/")
        encoded_key = _canonical_uri("/" + key).lstrip("/")
        if endpoint:
            # Path-style is the most interoperable shape for R2/MinIO/custom
            # S3 endpoints and avoids relying on wildcard bucket DNS.
            return f"{endpoint}/{quote(bucket, safe='-_.~')}/{encoded_key}"
        region = settings.storage_s3_region.strip()
        return f"https://{quote(bucket, safe='-_.~')}.s3.{region}.amazonaws.com/{encoded_key}"

    @classmethod
    def _signing_key(cls, date_stamp: str) -> bytes:
        settings = cls._settings()
        secret = settings.storage_s3_secret_key.get_secret_value().encode("utf-8")
        date_key = _hmac(b"AWS4" + secret, date_stamp)
        region_key = _hmac(date_key, settings.storage_s3_region.strip())
        service_key = _hmac(region_key, _SERVICE)
        return _hmac(service_key, "aws4_request")

    @classmethod
    def _signed_headers(
        cls,
        method: str,
        url: str,
        payload: bytes,
        extra_headers: dict[str, str] | None = None,
    ) -> dict[str, str]:
        settings = cls._settings()
        now = datetime.now(timezone.utc)
        amz_date = now.strftime("%Y%m%dT%H%M%SZ")
        date_stamp = now.strftime("%Y%m%d")
        parsed = urlsplit(url)
        payload_hash = _sha256_hex(payload)

        headers = {
            "host": parsed.netloc,
            "x-amz-content-sha256": payload_hash,
            "x-amz-date": amz_date,
        }
        for key, value in (extra_headers or {}).items():
            headers[key.lower()] = " ".join(value.strip().split())

        sorted_names = sorted(headers)
        canonical_headers = "".join(f"{name}:{headers[name]}\n" for name in sorted_names)
        signed_names = ";".join(sorted_names)
        canonical_request = "\n".join(
            [
                method.upper(),
                _canonical_uri(parsed.path),
                _canonical_query(list(parse_qsl(parsed.query, keep_blank_values=True))),
                canonical_headers,
                signed_names,
                payload_hash,
            ]
        )
        scope = f"{date_stamp}/{settings.storage_s3_region.strip()}/{_SERVICE}/aws4_request"
        string_to_sign = "\n".join(
            [
                _ALGORITHM,
                amz_date,
                scope,
                _sha256_hex(canonical_request.encode("utf-8")),
            ]
        )
        signature = hmac.new(
            cls._signing_key(date_stamp),
            string_to_sign.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

        result = {k: v for k, v in headers.items() if k != "host"}
        result["Authorization"] = (
            f"{_ALGORITHM} Credential={settings.storage_s3_access_key.get_secret_value().strip()}/{scope}, "
            f"SignedHeaders={signed_names}, Signature={signature}"
        )
        return result

    async def upload(self, storage_key: str, data: bytes, content_type: str) -> StoredFile:
        key = self._validate_key(storage_key)
        url = self._object_url(key)
        headers = self._signed_headers(
            "PUT",
            url,
            data,
            {"content-type": content_type},
        )
        headers["Content-Type"] = content_type
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.put(url, content=data, headers=headers)
        response.raise_for_status()
        return StoredFile(storage_key=key, size=len(data), content_type=content_type)

    async def download(self, storage_key: str) -> bytes:
        key = self._validate_key(storage_key)
        url = self._object_url(key)
        headers = self._signed_headers("GET", url, b"")
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.get(url, headers=headers)
        if response.status_code == 404:
            raise FileNotFoundError(f"File not found: {key}")
        response.raise_for_status()
        return response.content

    async def delete(self, storage_key: str) -> None:
        key = self._validate_key(storage_key)
        url = self._object_url(key)
        headers = self._signed_headers("DELETE", url, b"")
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.delete(url, headers=headers)
        if response.status_code not in {200, 204, 404}:
            response.raise_for_status()

    def get_url(self, storage_key: str) -> str | None:
        key = self._validate_key(storage_key)
        settings = self._settings()
        url = self._object_url(key)
        parsed = urlsplit(url)
        now = datetime.now(timezone.utc)
        amz_date = now.strftime("%Y%m%dT%H%M%SZ")
        date_stamp = now.strftime("%Y%m%d")
        scope = f"{date_stamp}/{settings.storage_s3_region.strip()}/{_SERVICE}/aws4_request"
        credential = f"{settings.storage_s3_access_key.get_secret_value().strip()}/{scope}"
        params = list(parse_qsl(parsed.query, keep_blank_values=True)) + [
            ("X-Amz-Algorithm", _ALGORITHM),
            ("X-Amz-Credential", credential),
            ("X-Amz-Date", amz_date),
            ("X-Amz-Expires", "300"),
            ("X-Amz-SignedHeaders", "host"),
        ]
        canonical_qs = _canonical_query(params)
        canonical_headers = f"host:{parsed.netloc}\n"
        canonical_request = "\n".join(
            [
                "GET",
                _canonical_uri(parsed.path),
                canonical_qs,
                canonical_headers,
                "host",
                "UNSIGNED-PAYLOAD",
            ]
        )
        string_to_sign = "\n".join(
            [
                _ALGORITHM,
                amz_date,
                scope,
                _sha256_hex(canonical_request.encode("utf-8")),
            ]
        )
        signature = hmac.new(
            self._signing_key(date_stamp),
            string_to_sign.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        final_query = canonical_qs + "&X-Amz-Signature=" + signature
        return urlunsplit((parsed.scheme, parsed.netloc, parsed.path, final_query, ""))
