from __future__ import annotations

import os
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, build_opener

from domain.update_manifest import UpdateManifest
from services.update_manifest_service import _SafeRedirectHandler, validate_source_url


class UpdateDownloadError(RuntimeError):
    pass


class UpdateDownloadCancelled(UpdateDownloadError):
    pass


class UpdateDownloadService:
    def __init__(self, staging_root: Path, *, timeout: float = 30.0, allow_test_http: bool = False) -> None:
        self.root = Path(staging_root)
        self.timeout = timeout
        self.allow_test_http = allow_test_http
        self._opener = build_opener(_SafeRedirectHandler(allow_test_http))

    def installer_path(self, manifest: UpdateManifest) -> Path:
        safe_version = manifest.version.replace("-", "_")
        path = (self.root / f"MMO-Video-Studio-{safe_version}-Setup.exe").resolve(strict=False)
        root = self.root.resolve(strict=False)
        if root != path.parent:
            raise UpdateDownloadError("Unsafe update staging path")
        return path

    def download(self, manifest: UpdateManifest, *, cancellation=None, progress=None) -> Path:
        self.root.mkdir(parents=True, exist_ok=True)
        target = self.installer_path(manifest)
        part = target.with_suffix(target.suffix + ".part")
        part.unlink(missing_ok=True)
        url = validate_source_url(manifest.installer_url, allow_local_http=self.allow_test_http)
        request = Request(url, headers={"Accept": "application/octet-stream"}, method="GET")
        written = 0
        try:
            with self._opener.open(request, timeout=self.timeout) as response, part.open("wb") as handle:
                validate_source_url(response.geturl(), allow_local_http=self.allow_test_http)
                while True:
                    if cancellation is not None and bool(getattr(cancellation, "is_cancelled", False)):
                        raise UpdateDownloadCancelled("Update download was cancelled")
                    chunk = response.read(256 * 1024)
                    if not chunk:
                        break
                    written += len(chunk)
                    if manifest.installer_size and written > manifest.installer_size:
                        raise UpdateDownloadError("Update download exceeded the expected installer size")
                    handle.write(chunk)
                    if progress:
                        progress(min(0.999, written / manifest.installer_size) if manifest.installer_size else 0.0)
            os.replace(part, target)
            if progress:
                progress(1.0)
            return target
        except UpdateDownloadCancelled:
            part.unlink(missing_ok=True)
            raise
        except UpdateDownloadError:
            part.unlink(missing_ok=True)
            target.unlink(missing_ok=True)
            raise
        except (HTTPError, URLError, OSError) as exc:
            part.unlink(missing_ok=True)
            target.unlink(missing_ok=True)
            raise UpdateDownloadError("Update download failed") from exc
