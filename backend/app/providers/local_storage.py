import os
from pathlib import Path

import aiofiles

from app.core.config import get_settings
from app.providers.storage import StorageProvider, StoredFile


class LocalStorageProvider(StorageProvider):
    """Store files on the local filesystem."""

    @property
    def name(self) -> str:
        return "local"

    def _base_path(self) -> Path:
        return Path(get_settings().storage_local_path)

    def _full_path(self, storage_key: str) -> Path:
        base = self._base_path().resolve()
        full = (base / storage_key).resolve()
        try:
            full.relative_to(base)
        except ValueError:
            raise ValueError("Invalid storage key")
        return full

    async def list_keys(self, prefix: str) -> list[str]:
        # No symlink traversal and no broad deletion. Keys are captured first;
        # the deletion executor separately validates and removes each file.
        if not prefix or not prefix.endswith("/") or prefix.startswith("/") or "\\" in prefix or "\x00" in prefix or any(part in {"", ".", ".."} for part in prefix[:-1].split("/")):
            raise ValueError("Invalid inventory prefix")
        base = self._base_path().absolute()
        directory = base / prefix
        candidate = base
        for part in prefix[:-1].split("/"):
            candidate = candidate / part
            if candidate.is_symlink():
                raise ValueError("Unsafe inventory path")
        directory.resolve().relative_to(base.resolve())
        if directory.is_symlink():
            raise ValueError("Unsafe storage directory")
        if not directory.exists():
            return []
        if not directory.is_dir():
            raise ValueError("Storage namespace is not a directory")
        keys = []
        def refuse_partial_inventory(error):
            raise error
        for root, directories, files in os.walk(directory, followlinks=False, onerror=refuse_partial_inventory):
            for name in directories + files:
                path = Path(root) / name
                if path.is_symlink():
                    raise ValueError("Unsafe storage inventory symlink")
            for name in files:
                path = Path(root) / name
                if not path.is_file():
                    raise ValueError("Unsafe storage inventory target")
                keys.append(path.relative_to(base).as_posix())
                if len(keys) > 100000:
                    raise ValueError("Storage inventory exceeds deletion batch limit")
        return sorted(keys)

    async def upload(self, storage_key: str, data: bytes, content_type: str) -> StoredFile:
        path = self._full_path(storage_key)
        path.parent.mkdir(parents=True, exist_ok=True)
        async with aiofiles.open(path, "wb") as f:
            await f.write(data)
        return StoredFile(storage_key=storage_key, size=len(data), content_type=content_type)

    async def download(self, storage_key: str) -> bytes:
        path = self._full_path(storage_key)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {storage_key}")
        async with aiofiles.open(path, "rb") as f:
            return await f.read()

    async def delete(self, storage_key: str) -> None:
        path = self._full_path(storage_key)
        if path.exists():
            os.remove(path)
