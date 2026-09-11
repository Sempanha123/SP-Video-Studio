from __future__ import annotations

import os
import shutil
from pathlib import Path
from typing import Callable, Protocol


class CancellationLike(Protocol):
    @property
    def is_cancelled(self) -> bool: ...


class MediaImportCancelled(RuntimeError):
    pass


class InsufficientDiskSpaceError(RuntimeError):
    pass


CopyProgress = Callable[[int, int], None]


class MediaImporter:
    """Streaming copy helper that never loads a complete media file into memory."""

    def __init__(self, *, chunk_size: int = 4 * 1024 * 1024) -> None:
        self.chunk_size = max(64 * 1024, int(chunk_size))

    def copy_into_project(
        self,
        source: str | Path,
        destination: str | Path,
        *,
        cancellation: CancellationLike | None = None,
        progress: CopyProgress | None = None,
    ) -> Path:
        source_path = Path(source)
        destination_path = Path(destination)
        size = source_path.stat().st_size
        destination_path.parent.mkdir(parents=True, exist_ok=True)
        free = shutil.disk_usage(destination_path.parent).free
        if free < size:
            raise InsufficientDiskSpaceError("Not enough disk space to import this file.")

        partial = destination_path.with_name(destination_path.name + ".part")
        partial.unlink(missing_ok=True)
        copied = 0
        try:
            with source_path.open("rb") as source_handle, partial.open("xb") as destination_handle:
                while True:
                    if cancellation is not None and cancellation.is_cancelled:
                        raise MediaImportCancelled("Import cancelled.")
                    chunk = source_handle.read(self.chunk_size)
                    if not chunk:
                        break
                    destination_handle.write(chunk)
                    copied += len(chunk)
                    if progress is not None:
                        progress(copied, size)
                destination_handle.flush()
                os.fsync(destination_handle.fileno())
            os.replace(partial, destination_path)
            try:
                shutil.copystat(source_path, destination_path, follow_symlinks=True)
            except OSError:
                pass
            if progress is not None:
                progress(size, size)
            return destination_path
        except Exception:
            partial.unlink(missing_ok=True)
            destination_path.unlink(missing_ok=True)
            raise
