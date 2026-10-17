"""Bound the bytes materialized for parsers after multipart spooling.

This does not replace ingress body/disk/concurrency limits or parser isolation.
"""
from fastapi import HTTPException, UploadFile


async def read_bounded_upload(file: UploadFile, *, max_bytes: int) -> bytes:
    if max_bytes <= 0:
        raise ValueError("Upload byte budget must be positive")
    # Never trust Content-Length, content type or the client-supplied filename.
    payload = await file.read(max_bytes + 1)
    if len(payload) > max_bytes:
        raise HTTPException(413, "File exceeds the configured upload size limit")
    return payload


async def read_storage_upload(file: UploadFile) -> bytes:
    """Apply the existing storage limit before materializing attachment/logo bytes.

    Preserve the attachment APIs' established 400 error contract. Billing still
    measures actual accepted bytes; declared multipart sizes remain untrusted.
    """
    from app.core.config import get_settings

    limit_mb = get_settings().storage_max_file_size_mb
    try:
        return await read_bounded_upload(file, max_bytes=limit_mb * 1024 * 1024)
    except HTTPException as exc:
        if exc.status_code != 413:
            raise
        raise HTTPException(400, f"File too large. Maximum size is {limit_mb} MB.") from None
