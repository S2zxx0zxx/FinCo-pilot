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
