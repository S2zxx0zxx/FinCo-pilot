import asyncio
from functools import lru_cache

import boto3
from botocore.client import Config
from botocore.exceptions import ClientError

from app.core.config import get_settings
from app.providers.storage import StorageProvider, StoredFile


class S3StorageProvider(StorageProvider):
    """S3-compatible attachment storage for horizontally scaled deployments.

    boto3 is synchronous; operations run in a worker thread so FastAPI's event
    loop is never blocked by network I/O. The same implementation works with
    AWS S3, Cloudflare R2, MinIO and other S3-compatible services.
    """

    @property
    def name(self) -> str:
        return "s3"

    @staticmethod
    def _validate_key(storage_key: str) -> str:
        key = storage_key.strip().lstrip("/")
        if not key or key.startswith("../") or "/../" in f"/{key}/":
            raise ValueError("Invalid storage key")
        return key

    @staticmethod
    @lru_cache(maxsize=1)
    def _client():
        settings = get_settings()
        kwargs: dict[str, object] = {
            "service_name": "s3",
            "region_name": settings.storage_s3_region or None,
            "endpoint_url": settings.storage_s3_endpoint_url or None,
            "config": Config(signature_version="s3v4"),
        }
        access_key = settings.storage_s3_access_key.get_secret_value().strip()
        secret_key = settings.storage_s3_secret_key.get_secret_value().strip()
        if access_key:
            kwargs["aws_access_key_id"] = access_key
        if secret_key:
            kwargs["aws_secret_access_key"] = secret_key
        return boto3.client(**kwargs)

    @staticmethod
    def _bucket() -> str:
        bucket = get_settings().storage_s3_bucket.strip()
        if not bucket:
            raise RuntimeError("STORAGE_S3_BUCKET is required when STORAGE_PROVIDER=s3")
        return bucket

    async def upload(self, storage_key: str, data: bytes, content_type: str) -> StoredFile:
        key = self._validate_key(storage_key)
        client = self._client()
        bucket = self._bucket()
        await asyncio.to_thread(
            client.put_object,
            Bucket=bucket,
            Key=key,
            Body=data,
            ContentType=content_type,
            ServerSideEncryption="AES256",
        )
        return StoredFile(storage_key=key, size=len(data), content_type=content_type)

    async def download(self, storage_key: str) -> bytes:
        key = self._validate_key(storage_key)
        client = self._client()
        bucket = self._bucket()
        try:
            response = await asyncio.to_thread(client.get_object, Bucket=bucket, Key=key)
        except ClientError as exc:
            code = str(exc.response.get("Error", {}).get("Code", ""))
            if code in {"NoSuchKey", "404", "NotFound"}:
                raise FileNotFoundError(f"File not found: {key}") from exc
            raise
        body = response["Body"]
        return await asyncio.to_thread(body.read)

    async def delete(self, storage_key: str) -> None:
        key = self._validate_key(storage_key)
        client = self._client()
        await asyncio.to_thread(client.delete_object, Bucket=self._bucket(), Key=key)

    def get_url(self, storage_key: str) -> str | None:
        key = self._validate_key(storage_key)
        client = self._client()
        return client.generate_presigned_url(
            "get_object",
            Params={"Bucket": self._bucket(), "Key": key},
            ExpiresIn=300,
        )
