from __future__ import annotations

import logging
import os
import shutil
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable
from uuid import uuid4

from domain.ai_model import AIModel
from domain.model_installation import MODEL_MANIFEST_SCHEMA_VERSION
from domain.project import utc_now_iso
from engines.model_sources import DownloadCancelled, ModelSource, ModelSourceError, RemoteModelFile
from services.model_verification_service import ModelVerificationService
from storage.json_writer import atomic_write_json
from workers.cancellation import CancellationToken


class ModelDownloadError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class ModelDownloadProgress:
    model_id: str
    downloaded_bytes: int
    total_bytes: int
    speed_bytes_per_second: float
    current_file: str
    state: str

    @property
    def fraction(self) -> float:
        if self.total_bytes <= 0:
            return 0.0
        return max(0.0, min(1.0, self.downloaded_bytes / self.total_bytes))


class ModelDownloadService:
    def __init__(
        self,
        model_root: Path,
        source: ModelSource,
        verifier: ModelVerificationService,
        logger: logging.Logger | None = None,
        retries: int = 3,
        backoff_seconds: float = 0.4,
    ) -> None:
        self.model_root = Path(model_root)
        self.source = source
        self.verifier = verifier
        self.logger = logger or logging.getLogger("sp_video_studio.models.download")
        self.retries = max(1, int(retries))
        self.backoff_seconds = max(0.0, float(backoff_seconds))
        self.download_root = self.model_root / ".downloads"

    def install(
        self,
        model: AIModel,
        cancellation: CancellationToken,
        progress_callback: Callable[[ModelDownloadProgress], None] | None = None,
    ) -> Path:
        self.model_root.mkdir(parents=True, exist_ok=True)
        self.download_root.mkdir(parents=True, exist_ok=True)
        stage = self.download_root / model.model_id
        stage.mkdir(parents=True, exist_ok=True)
        files = self.source.list_files(model)
        if not files:
            raise ModelDownloadError("The model source did not provide any files.")
        total = sum(item.size or 0 for item in files)
        completed_before = sum(
            item.size or 0
            for item in files
            if item.size is not None and (stage / item.path).is_file() and (stage / item.path).stat().st_size == item.size
        )
        started = time.monotonic()
        last_sample_time = started
        last_sample_bytes = completed_before
        smoothed_speed = 0.0
        completed_base = 0

        for remote in files:
            if cancellation.is_cancelled:
                raise DownloadCancelled("Model download cancelled.")
            final_stage_file = _safe_child(stage, remote.path)
            if remote.size is not None and final_stage_file.is_file() and final_stage_file.stat().st_size == remote.size:
                completed_base += remote.size
                continue
            part = final_stage_file.with_name(final_stage_file.name + ".part")
            if final_stage_file.exists():
                final_stage_file.unlink()

            def on_file_progress(file_bytes: int, file_total: int | None) -> None:
                nonlocal last_sample_time, last_sample_bytes, smoothed_speed
                aggregate = completed_base + file_bytes
                now = time.monotonic()
                elapsed = now - last_sample_time
                if elapsed >= 0.2:
                    instant = max(0, aggregate - last_sample_bytes) / max(elapsed, 0.001)
                    smoothed_speed = instant if smoothed_speed <= 0 else smoothed_speed * 0.72 + instant * 0.28
                    last_sample_time = now
                    last_sample_bytes = aggregate
                if progress_callback:
                    progress_callback(
                        ModelDownloadProgress(
                            model.model_id,
                            aggregate,
                            total or (completed_base + (file_total or 0)),
                            smoothed_speed,
                            remote.path,
                            "downloading",
                        )
                    )

            self._download_with_retry(remote, part, cancellation, on_file_progress)
            if remote.size is not None and part.stat().st_size != remote.size:
                raise ModelDownloadError(f"Downloaded file size did not match: {remote.path}")
            final_stage_file.parent.mkdir(parents=True, exist_ok=True)
            os.replace(part, final_stage_file)
            completed_base += final_stage_file.stat().st_size

        if cancellation.is_cancelled:
            raise DownloadCancelled("Model download cancelled.")
        if progress_callback:
            progress_callback(ModelDownloadProgress(model.model_id, completed_base, total or completed_base, smoothed_speed, "", "verifying"))
        manifest = {
            "app_model_schema_version": MODEL_MANIFEST_SCHEMA_VERSION,
            "model_id": model.model_id,
            "model_version": model.version,
            "source": model.source,
            "source_identifier": model.source_identifier,
            "source_revision": files[0].revision if files else None,
            "installed_at": utc_now_iso(),
            "files": [
                {
                    "path": item.path,
                    "size": (stage / item.path).stat().st_size if (stage / item.path).is_file() else item.size,
                    "sha256": item.sha256,
                }
                for item in files
            ],
            "verification": "pending",
        }
        atomic_write_json(stage / "model_manifest.json", manifest)
        verification = self.verifier.verify(model, stage)
        if not verification.valid:
            raise ModelDownloadError("Downloaded model files did not pass verification: " + "; ".join(verification.errors[:3]))
        manifest["verification"] = "verified"
        manifest["verified_at"] = utc_now_iso()
        atomic_write_json(stage / "model_manifest.json", manifest)
        final_path = _safe_child(self.model_root, model.install_relative_path)
        self._commit_stage(stage, final_path)
        if progress_callback:
            progress_callback(ModelDownloadProgress(model.model_id, completed_base, total or completed_base, smoothed_speed, "", "completed"))
        return final_path

    def partial_path(self, model_id: str) -> Path:
        return _safe_child(self.download_root, model_id)

    def remove_partial(self, model_id: str) -> None:
        target = self.partial_path(model_id)
        if target.exists():
            shutil.rmtree(target)

    def _download_with_retry(
        self,
        remote: RemoteModelFile,
        part: Path,
        cancellation: CancellationToken,
        progress: Callable[[int, int | None], None],
    ) -> None:
        last_error: Exception | None = None
        for attempt in range(self.retries):
            if cancellation.is_cancelled:
                raise DownloadCancelled("Model download cancelled.")
            try:
                self.source.download_file(remote, part, cancellation, progress)
                return
            except DownloadCancelled:
                raise
            except (ModelSourceError, OSError) as exc:
                last_error = exc
                if attempt + 1 >= self.retries:
                    break
                if self.backoff_seconds:
                    time.sleep(self.backoff_seconds * (2**attempt))
        raise ModelDownloadError(str(last_error or "Model download failed.")) from last_error

    def _commit_stage(self, stage: Path, final_path: Path) -> None:
        final_path.parent.mkdir(parents=True, exist_ok=True)
        backup: Path | None = None
        try:
            if final_path.exists():
                backup = self.download_root / f".backup-{final_path.name}-{uuid4().hex[:8]}"
                os.replace(final_path, backup)
            os.replace(stage, final_path)
        except Exception:
            if backup is not None and backup.exists() and not final_path.exists():
                os.replace(backup, final_path)
            raise
        else:
            if backup is not None and backup.exists():
                shutil.rmtree(backup, ignore_errors=True)


def _safe_child(root: Path, relative: str | Path) -> Path:
    relative_path = Path(relative)
    if relative_path.is_absolute() or any(part in {"", ".", ".."} for part in relative_path.parts):
        raise ModelDownloadError("Unsafe model path.")
    root_resolved = root.resolve()
    target = (root / relative_path).resolve()
    if target == root_resolved or root_resolved not in target.parents:
        raise ModelDownloadError("Model path escapes the managed model directory.")
    return target
