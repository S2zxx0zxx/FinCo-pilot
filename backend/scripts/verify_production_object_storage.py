"""Credential-safe production object-storage acceptance probe.

Creates one random temporary object, verifies HEAD + byte-for-byte download,
deletes it, then confirms it is gone. It never prints credentials, bucket names,
endpoints, object keys, provider response bodies, or application data.
"""

from __future__ import annotations

import argparse
import asyncio
import secrets
import sys

from app.core.config import get_settings
from app.providers import get_storage_provider
from app.providers.s3_storage import S3StorageProvider


async def _run(ci_mode: bool) -> None:
    settings = get_settings()
    if not ci_mode and not settings.is_production:
        raise RuntimeError(
            "Production acceptance requires DEPLOYMENT_ENVIRONMENT=production"
        )
    if settings.storage_provider != "s3":
        raise RuntimeError("Object-storage acceptance requires STORAGE_PROVIDER=s3")

    provider = get_storage_provider()
    if not isinstance(provider, S3StorageProvider):
        raise RuntimeError("Configured storage provider is not the S3 runtime")

    nonce = secrets.token_hex(16)
    key = f"__fincopilot_acceptance__/{nonce}.bin"
    payload = ("finco-object-storage-acceptance:" + nonce).encode("utf-8")

    try:
        stored = await provider.upload(key, payload, "application/octet-stream")
        if stored.size != len(payload):
            raise RuntimeError("Object storage reported an unexpected uploaded size")

        head = await provider.verify_exists(key)
        if head.size != len(payload):
            raise RuntimeError("Object storage HEAD size did not match the upload")

        downloaded = await provider.download(key)
        if not secrets.compare_digest(downloaded, payload):
            raise RuntimeError("Object storage byte-for-byte round-trip failed")

        await provider.delete(key)
        try:
            await provider.download(key)
        except FileNotFoundError:
            pass
        else:
            raise RuntimeError("Deleted acceptance object is still readable")
    finally:
        # Idempotent cleanup protects repeated/partially failed probes.
        try:
            await provider.delete(key)
        except Exception:
            pass


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--ci",
        action="store_true",
        help="allow an explicitly configured disposable development S3 endpoint",
    )
    args = parser.parse_args()

    try:
        asyncio.run(_run(args.ci))
    except Exception as exc:  # noqa: BLE001 - provider details stay sanitized
        print(
            f"Object-storage acceptance failed: {type(exc).__name__}",
            file=sys.stderr,
        )
        return 1

    print("FinCo-Pilot object-storage acceptance: PASS")
    print("write_head_read_delete_roundtrip=pass")
    print("integrity_metadata=verified")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
