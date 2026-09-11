from __future__ import annotations

import json
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Protocol

from domain.ai_model import AIModel
from workers.cancellation import CancellationToken


class ModelSourceError(RuntimeError):
    pass


class DownloadCancelled(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class RemoteModelFile:
    path: str
    size: int | None
    url: str
    sha256: str | None = None
    revision: str | None = None


class ModelSource(Protocol):
    def list_files(self, model: AIModel) -> list[RemoteModelFile]: ...

    def download_file(
        self,
        remote: RemoteModelFile,
        destination: Path,
        cancellation: CancellationToken,
        progress: Callable[[int, int | None], None],
    ) -> int: ...


class HuggingFaceSource:
    """Public Hugging Face model source with HTTP Range resume support."""

    def __init__(self, timeout: float = 30.0, user_agent: str = "SP-Video-Studio/0.1") -> None:
        self.timeout = timeout
        self.user_agent = user_agent

    def list_files(self, model: AIModel) -> list[RemoteModelFile]:
        identifier = urllib.parse.quote(model.source_identifier, safe="/")
        url = f"https://huggingface.co/api/models/{identifier}?blobs=true"
        request = urllib.request.Request(url, headers={"User-Agent": self.user_agent})
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except (OSError, urllib.error.URLError, urllib.error.HTTPError, json.JSONDecodeError) as exc:
            raise ModelSourceError("Model catalog could not be read from Hugging Face.") from exc

        siblings = payload.get("siblings") if isinstance(payload, dict) else None
        if not isinstance(siblings, list):
            raise ModelSourceError("The model source returned an invalid file catalog.")

        revision = str(payload.get("sha") or "main") if isinstance(payload, dict) else "main"
        files: list[RemoteModelFile] = []
        for item in siblings:
            if not isinstance(item, dict):
                continue
            relative = str(item.get("rfilename") or "")
            if not relative or _skip_repository_file(relative):
                continue
            _validate_relative_path(relative)
            lfs = item.get("lfs") if isinstance(item.get("lfs"), dict) else {}
            size_value = lfs.get("size", item.get("size"))
            try:
                size = int(size_value) if size_value is not None else None
            except (TypeError, ValueError):
                size = None
            oid = str(lfs.get("sha256") or lfs.get("oid") or "")
            if oid.startswith("sha256:"):
                oid = oid.split(":", 1)[1]
            sha256 = oid.lower() if len(oid) == 64 and all(ch in "0123456789abcdefABCDEF" for ch in oid) else None
            quoted_path = "/".join(urllib.parse.quote(part, safe="") for part in relative.split("/"))
            revision_path = urllib.parse.quote(revision, safe="")
            download_url = f"https://huggingface.co/{identifier}/resolve/{revision_path}/{quoted_path}?download=true"
            files.append(RemoteModelFile(relative, size, download_url, sha256, revision))

        if not files:
            raise ModelSourceError("No downloadable model files were found.")
        return files

    def download_file(
        self,
        remote: RemoteModelFile,
        destination: Path,
        cancellation: CancellationToken,
        progress: Callable[[int, int | None], None],
    ) -> int:
        destination.parent.mkdir(parents=True, exist_ok=True)
        existing = destination.stat().st_size if destination.exists() else 0
        headers = {"User-Agent": self.user_agent}
        if existing > 0:
            headers["Range"] = f"bytes={existing}-"
        request = urllib.request.Request(remote.url, headers=headers)
        try:
            response = urllib.request.urlopen(request, timeout=self.timeout)
        except urllib.error.HTTPError as exc:
            if exc.code == 404:
                raise ModelSourceError("Model files could not be found at the configured source.") from exc
            if exc.code == 403:
                raise ModelSourceError("The model source refused this download request.") from exc
            raise ModelSourceError(f"Model download failed with HTTP {exc.code}.") from exc
        except (OSError, urllib.error.URLError) as exc:
            raise ModelSourceError("Download could not start because the network is unavailable.") from exc

        with response:
            resumed = existing > 0 and getattr(response, "status", None) == 206
            if existing > 0 and not resumed:
                existing = 0
            mode = "ab" if resumed else "wb"
            expected_total = remote.size
            if expected_total is None:
                length = response.headers.get("Content-Length")
                if length and length.isdigit():
                    expected_total = existing + int(length)
            downloaded = existing
            progress(downloaded, expected_total)
            try:
                with destination.open(mode) as handle:
                    while True:
                        if cancellation.is_cancelled:
                            handle.flush()
                            raise DownloadCancelled("Model download cancelled.")
                        chunk = response.read(1024 * 1024)
                        if not chunk:
                            break
                        handle.write(chunk)
                        downloaded += len(chunk)
                        progress(downloaded, expected_total)
            except DownloadCancelled:
                raise
            except OSError as exc:
                raise ModelSourceError("The model file could not be written to disk.") from exc
        return downloaded


def _skip_repository_file(path: str) -> bool:
    name = path.rsplit("/", 1)[-1].lower()
    return name in {"readme.md", ".gitattributes", ".gitignore"} or path.startswith(".git/")


def _validate_relative_path(path: str) -> None:
    candidate = Path(path)
    if candidate.is_absolute() or not candidate.parts or any(part in {"", ".", ".."} for part in candidate.parts):
        raise ModelSourceError("The model source returned an unsafe file path.")
