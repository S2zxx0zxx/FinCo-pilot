"""Exact local-file deletion through directory descriptors; never follow symlinks."""
import os
import stat
from pathlib import Path


def delete_managed_file(base: Path, relative: str) -> None:
    parts = relative.split('/')
    if not relative or relative.startswith('/') or '\\' in relative or '\x00' in relative or any(p in {'', '.', '..'} for p in parts):
        raise ValueError('Invalid deletion file key')
    descriptors = []
    try:
        try:
            directory = os.open(base, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        except FileNotFoundError:
            return
        descriptors.append(directory)
        for part in parts[:-1]:
            try:
                directory = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=directory)
            except FileNotFoundError:
                return
            descriptors.append(directory)
        try:
            info = os.stat(parts[-1], dir_fd=directory, follow_symlinks=False)
        except FileNotFoundError:
            return
        if not stat.S_ISREG(info.st_mode):
            raise ValueError('Deletion requires a regular file')
        # A concurrent replacement with a symlink can at most unlink that link;
        # it cannot delete the referenced target through this directory fd.
        os.unlink(parts[-1], dir_fd=directory)
    finally:
        for descriptor in reversed(descriptors):
            os.close(descriptor)
