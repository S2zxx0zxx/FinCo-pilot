import hashlib
import hmac
from datetime import datetime, timezone
from urllib.parse import parse_qsl, quote, urlsplit, urlunsplit

import httpx

from app.core.config import get_settings
from app.providers.storage import StorageProvider, StoredFile


_ALGORITHM = "AWS4-HMAC-SHA256"
_SERVICE = "s3"
_INTEGRITY_HEADER = "x-amz-meta-fincopilot-sha256"


class StorageIntegrityError(RuntimeError):
    """Stored bytes did not match FinCopilot upload-time integrity metadata."""


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
    """Private S3-compatible object storage with explicit SigV4.

    Roadmap #16 selects Cloudflare R2 for the zero-cost production path, while
    this adapter intentionally stays S3-compatible so an operator can migrate
    to AWS S3 or another private S3 endpoint without changing attachment rows.

    Stored database keys are logical keys. STORAGE_S3_PREFIX is applied only at
    the provider boundary, which keeps one bucket safely namespaced while
    avoiding provider-specific identifiers in application records.
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
        if (
            not key
            or key == ".."
            or key.startswith("../")
            or "/../" in f"/{key}/"
            or "\\..\\" in f"\\{key}\\"
        ):
            raise ValueError("Invalid storage key")
        return key

    @classmethod
    def _qualified_key(cls, storage_key: str) -> str:
        key = cls._validate_key(storage_key)
        prefix = cls._settings().storage_s3_prefix.strip().strip("/")
        return f"{prefix}/{key}" if prefix else key

    @classmethod
    def _object_url(cls, qualified_key: str) -> str:
        settings = cls._settings()
        bucket = settings.storage_s3_bucket.strip()
        endpoint = settings.storage_s3_endpoint_url.strip().rstrip("/")
        encoded_key = _canonical_uri("/" + qualified_key).lstrip("/")
        if endpoint:
            # R2 and many private S3-compatible endpoints use path-style bucket
            # addressing. Config validation requires a bare origin so a crafted
            # endpoint cannot smuggle path/query material into the signature.
            return f"{endpoint}/{quote(bucket, safe='-_.~')}/{encoded_key}"
        region = settings.storage_s3_region.strip()
        return (
            f"https://{quote(bucket, safe='-_.~')}.s3.{region}.amazonaws.com/"
            f"{encoded_key}"
        )

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
        scope = (
            f"{date_stamp}/{settings.storage_s3_region.strip()}/{_SERVICE}/aws4_request"
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
            cls._signing_key(date_stamp),
            string_to_sign.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

        result = {k: v for k, v in headers.items() if k != "host"}
        result["Authorization"] = (
            f"{_ALGORITHM} Credential="
            f"{settings.storage_s3_access_key.get_secret_value().strip()}/{scope}, "
            f"SignedHeaders={signed_names}, Signature={signature}"
        )
        return result

    @classmethod
    def _timeout(cls) -> httpx.Timeout:
        seconds = float(cls._settings().storage_s3_request_timeout_seconds)
        return httpx.Timeout(seconds, connect=min(seconds, 10.0))

    async def upload(
        self, storage_key: str, data: bytes, content_type: str
    ) -> StoredFile:
        logical_key = self._validate_key(storage_key)
        qualified_key = self._qualified_key(logical_key)
        url = self._object_url(qualified_key)
        checksum = _sha256_hex(data)
        headers = self._signed_headers(
            "PUT",
            url,
            data,
            {
                "content-type": content_type,
                _INTEGRITY_HEADER: checksum,
            },
        )
        async with httpx.AsyncClient(
            timeout=self._timeout(), follow_redirects=False
        ) as client:
            response = await client.put(url, content=data, headers=headers)
        response.raise_for_status()
        return StoredFile(
            storage_key=logical_key,
            size=len(data),
            content_type=content_type,
        )

    async def download(self, storage_key: str) -> bytes:
        logical_key = self._validate_key(storage_key)
        url = self._object_url(self._qualified_key(logical_key))
        headers = self._signed_headers("GET", url, b"")
        async with httpx.AsyncClient(
            timeout=self._timeout(), follow_redirects=False
        ) as client:
            response = await client.get(url, headers=headers)
        if response.status_code == 404:
            raise FileNotFoundError(f"File not found: {logical_key}")
        response.raise_for_status()

        max_bytes = self._settings().storage_max_file_size_mb * 1024 * 1024
        if len(response.content) > max_bytes:
            raise StorageIntegrityError(
                "Stored object exceeds the configured maximum size"
            )

        expected_checksum = response.headers.get(_INTEGRITY_HEADER)
        if expected_checksum:
            expected_checksum = expected_checksum.strip().lower()
            actual_checksum = _sha256_hex(response.content)
            if not hmac.compare_digest(expected_checksum, actual_checksum):
                raise StorageIntegrityError(
                    "Stored object checksum verification failed"
                )
        return response.content

    async def delete(self, storage_key: str) -> None:
        logical_key = self._validate_key(storage_key)
        url = self._object_url(self._qualified_key(logical_key))
        headers = self._signed_headers("DELETE", url, b"")
        async with httpx.AsyncClient(
            timeout=self._timeout(), follow_redirects=False
        ) as client:
            response = await client.delete(url, headers=headers)
        if response.status_code not in {200, 204, 404}:
            response.raise_for_status()

    async def verify_exists(self, storage_key: str) -> StoredFile:
        """HEAD an object without returning bytes; used by acceptance probes."""
        logical_key = self._validate_key(storage_key)
        url = self._object_url(self._qualified_key(logical_key))
        headers = self._signed_headers("HEAD", url, b"")
        async with httpx.AsyncClient(
            timeout=self._timeout(), follow_redirects=False
        ) as client:
            response = await client.head(url, headers=headers)
        if response.status_code == 404:
            raise FileNotFoundError(f"File not found: {logical_key}")
        response.raise_for_status()

        try:
            size = int(response.headers.get("content-length", "0"))
        except ValueError as exc:
            raise StorageIntegrityError(
                "Storage returned an invalid Content-Length"
            ) from exc
        return StoredFile(
            storage_key=logical_key,
            size=size,
            content_type=response.headers.get(
                "content-type", "application/octet-stream"
            ),
        )

    def get_url(self, storage_key: str) -> str | None:
        logical_key = self._validate_key(storage_key)
        settings = self._settings()
        url = self._object_url(self._qualified_key(logical_key))
        parsed = urlsplit(url)
        now = datetime.now(timezone.utc)
        amz_date = now.strftime("%Y%m%dT%H%M%SZ")
        date_stamp = now.strftime("%Y%m%d")
        scope = (
            f"{date_stamp}/{settings.storage_s3_region.strip()}/{_SERVICE}/aws4_request"
        )
        credential = (
            f"{settings.storage_s3_access_key.get_secret_value().strip()}/{scope}"
        )
        params = list(parse_qsl(parsed.query, keep_blank_values=True)) + [
            ("X-Amz-Algorithm", _ALGORITHM),
            ("X-Amz-Credential", credential),
            ("X-Amz-Date", amz_date),
            ("X-Amz-Expires", str(settings.storage_s3_presign_ttl_seconds)),
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
        return urlunsplit(
            (parsed.scheme, parsed.netloc, parsed.path, final_query, "")
        )
