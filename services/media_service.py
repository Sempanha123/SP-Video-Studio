from __future__ import annotations

import logging
import os
import shutil
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Protocol, TYPE_CHECKING
from uuid import uuid4

from PIL import Image, ImageOps, UnidentifiedImageError

from domain.media import MediaAsset, MediaStatus, MediaType, media_utc_now_iso
from domain.project import Project
from media.file_classifier import FileClassifier
from media.media_importer import (
    InsufficientDiskSpaceError,
    MediaImportCancelled,
    MediaImporter,
)
from media.probe import FFprobeService, InvalidMediaError, MediaProbeError, MediaProbeResult
from media.thumbnails import ThumbnailError, ThumbnailService
from storage.repositories.media_repository import MediaRepository
from storage.repositories.project_repository import ProjectRepository

if TYPE_CHECKING:
    from workers.cancellation import CancellationToken


class MediaServiceError(RuntimeError):
    user_message = "SP Video Studio could not complete this media action."


class UnsupportedMediaError(MediaServiceError):
    user_message = "This file format is not supported yet."


class MediaFilesMissingError(MediaServiceError):
    user_message = "The project media file could not be found."


class MediaProjectError(MediaServiceError):
    user_message = "Open a valid project before importing media."


class UnsafeMediaPathError(MediaServiceError):
    user_message = "SP Video Studio refused an unsafe media file operation."


class MediaImportError(MediaServiceError):
    user_message = "This media file could not be imported."


ProgressCallback = Callable[[str, float], None]
BatchProgressCallback = Callable[[int, int, str, str, float], None]


@dataclass(slots=True)
class MediaImportFailure:
    path: str
    name: str
    reason: str


@dataclass(slots=True)
class MediaImportSummary:
    imported: list[MediaAsset] = field(default_factory=list)
    failures: list[MediaImportFailure] = field(default_factory=list)
    cancelled: bool = False

    @property
    def imported_count(self) -> int:
        return len(self.imported)

    @property
    def failed_count(self) -> int:
        return len(self.failures)


class CancellationLike(Protocol):
    @property
    def is_cancelled(self) -> bool: ...


class MediaService:
    """Coordinates safe project-local media copies, metadata, thumbnails and persistence."""

    def __init__(
        self,
        repository: MediaRepository,
        project_repository: ProjectRepository,
        prober: FFprobeService,
        thumbnails: ThumbnailService,
        *,
        classifier: FileClassifier | None = None,
        importer: MediaImporter | None = None,
        logger: logging.Logger | None = None,
    ) -> None:
        self.repository = repository
        self.project_repository = project_repository
        self.prober = prober
        self.thumbnails = thumbnails
        self.classifier = classifier or FileClassifier()
        self.importer = importer or MediaImporter()
        self.logger = logger or logging.getLogger("sp_video_studio.media")

    def import_file(
        self,
        project_id: str,
        source: str | Path,
        *,
        cancellation: CancellationLike | None = None,
        progress: ProgressCallback | None = None,
    ) -> MediaAsset:
        project = self._require_project(project_id)
        source_path = Path(source).expanduser()
        try:
            source_path = source_path.resolve(strict=True)
        except OSError as exc:
            raise MediaImportError("The selected file could not be found.") from exc
        if not source_path.is_file():
            raise MediaImportError("The selected path is not a file.")

        media_type = self.classifier.classify(source_path)
        if media_type is None:
            extension = source_path.suffix.lower() or "(none)"
            raise UnsupportedMediaError(f"This file format is not supported yet: {extension}")

        project_root = Path(project.project_path)
        if not project_root.is_dir() or not (project_root / "project.json").is_file():
            raise MediaProjectError("Project files could not be found.")

        asset_id = str(uuid4())
        extension = source_path.suffix.lower()
        destination_dir = self._media_directory(project_root, media_type)
        destination_dir.mkdir(parents=True, exist_ok=True)
        destination = destination_dir / f"{asset_id}{extension}"
        while destination.exists():
            asset_id = str(uuid4())
            destination = destination_dir / f"{asset_id}{extension}"
        thumbnail = project_root / "thumbnails" / f"{asset_id}.jpg"
        copied = False
        thumbnail_created = False

        self.logger.info("Media import started: %s (%s)", source_path.name, media_type)
        self._emit_progress(progress, "Preparing", 0.02)
        self._raise_if_cancelled(cancellation)

        try:
            def copy_progress(done: int, total: int) -> None:
                ratio = (done / total) if total else 1.0
                self._emit_progress(progress, "Copying", 0.05 + ratio * 0.55)

            self.importer.copy_into_project(
                source_path,
                destination,
                cancellation=cancellation,
                progress=copy_progress,
            )
            copied = True
            self._raise_if_cancelled(cancellation)
            self._emit_progress(progress, "Analyzing", 0.65)

            if media_type in {MediaType.VIDEO.value, MediaType.AUDIO.value}:
                probe = self.prober.probe(destination, expected_type=media_type)
                image_metadata: dict[str, object] = {}
            else:
                probe, image_metadata = self._probe_image(destination)

            self._raise_if_cancelled(cancellation)
            thumbnail_path: str | None = None
            if media_type in {MediaType.VIDEO.value, MediaType.IMAGE.value}:
                self._emit_progress(progress, "Generating Thumbnail", 0.82)
                try:
                    result = self.thumbnails.generate(
                        media_type,
                        destination,
                        thumbnail,
                        duration_ms=probe.duration_ms,
                    )
                    if result is not None:
                        thumbnail_path = str(result)
                        thumbnail_created = True
                except ThumbnailError:
                    self.logger.warning(
                        "Thumbnail generation failed for %s", source_path.name, exc_info=True
                    )

            self._raise_if_cancelled(cancellation)
            stat = source_path.stat()
            created_at = datetime.fromtimestamp(stat.st_ctime, timezone.utc).isoformat()
            metadata = probe.metadata()
            metadata.update(image_metadata)
            asset = MediaAsset(
                asset_id=asset_id,
                project_id=project_id,
                media_type=media_type,
                name=source_path.name,
                original_path=str(source_path),
                project_path=str(destination),
                thumbnail_path=thumbnail_path,
                duration_ms=probe.duration_ms,
                width=probe.width,
                height=probe.height,
                fps=probe.fps,
                codec=probe.codec,
                audio_codec=probe.audio_codec,
                sample_rate=probe.sample_rate,
                channels=probe.channels,
                file_size=destination.stat().st_size,
                mime_type=self.classifier.mime_type(source_path),
                extension=extension,
                created_at=created_at,
                imported_at=media_utc_now_iso(),
                status=MediaStatus.READY,
                metadata_json=metadata,
            )
            asset.validate()
            self.repository.create(asset)
            self._emit_progress(progress, "Completed", 1.0)
            self.logger.info("Media import completed: %s (%s)", asset.asset_id, source_path.name)
            return asset
        except (UnsupportedMediaError, MediaImportCancelled, InsufficientDiskSpaceError):
            self._cleanup_import(destination, thumbnail)
            self.logger.info("Media import cancelled/blocked: %s", source_path.name)
            raise
        except InvalidMediaError as exc:
            self._cleanup_import(destination, thumbnail)
            self.logger.warning("Media probe failed for %s: %s", source_path.name, exc)
            raise MediaImportError(
                f"{source_path.name} could not be imported because it is not a valid or supported {media_type} file."
            ) from exc
        except MediaProbeError as exc:
            self._cleanup_import(destination, thumbnail)
            self.logger.warning("Media inspection unavailable for %s: %s", source_path.name, exc)
            raise MediaImportError(str(exc) or "Media inspection is unavailable.") from exc
        except Exception as exc:
            if copied or thumbnail_created:
                self._cleanup_import(destination, thumbnail)
            self.logger.exception("Media import failed: %s", source_path.name)
            if isinstance(exc, MediaServiceError):
                raise
            raise MediaImportError(
                f"SP Video Studio could not import {source_path.name}."
            ) from exc

    def import_many(
        self,
        project_id: str,
        sources: list[str | Path],
        *,
        cancellation: CancellationLike | None = None,
        progress: BatchProgressCallback | None = None,
    ) -> MediaImportSummary:
        summary = MediaImportSummary()
        total = len(sources)
        for index, source in enumerate(sources, start=1):
            if cancellation is not None and cancellation.is_cancelled:
                summary.cancelled = True
                break
            path = Path(source)
            try:
                asset = self.import_file(
                    project_id,
                    path,
                    cancellation=cancellation,
                    progress=(
                        (lambda stage, fraction, i=index, n=path.name: progress(i, total, n, stage, fraction))
                        if progress is not None
                        else None
                    ),
                )
                summary.imported.append(asset)
            except MediaImportCancelled:
                summary.cancelled = True
                break
            except Exception as exc:
                reason = str(exc).strip() or getattr(exc, "user_message", "Import failed.")
                summary.failures.append(
                    MediaImportFailure(path=str(path), name=path.name, reason=reason)
                )
                self.logger.warning("Media import failed for %s: %s", path.name, reason)
        return summary

    def get_media(self, project_id: str, asset_id: str) -> MediaAsset:
        asset = self.repository.get_by_id(asset_id)
        if asset is None or asset.project_id != project_id:
            raise MediaServiceError("This media item could not be found in the current project.")
        return asset

    def list_media(
        self,
        project_id: str,
        *,
        search: str = "",
        media_type: str = "all",
        sort: str = "recent",
    ) -> list[MediaAsset]:
        return self.repository.list_by_project(
            project_id,
            search=search,
            media_type=media_type,
            sort=sort,
        )

    def refresh_missing(self, project_id: str) -> int:
        changed = 0
        for asset in self.repository.list_by_project(project_id):
            exists = Path(asset.project_path).is_file()
            current = str(asset.status)
            desired = current
            if not exists and current in {MediaStatus.READY.value, MediaStatus.PROCESSING.value}:
                desired = MediaStatus.MISSING.value
            elif exists and current == MediaStatus.MISSING.value:
                desired = MediaStatus.READY.value
            if desired != current:
                self.repository.update_status(asset.asset_id, desired)
                changed += 1
        return changed

    def remove_media(self, project_id: str, asset_id: str) -> None:
        project = self._require_project(project_id)
        asset = self.repository.get_by_id(asset_id)
        if asset is None or asset.project_id != project_id:
            raise MediaServiceError("This media item does not belong to the current project.")

        project_root = Path(project.project_path).resolve()
        managed_root = (project_root / "media").resolve()
        thumbnail_root = (project_root / "thumbnails").resolve()
        cache_root = project_root / "cache"
        cache_root.mkdir(parents=True, exist_ok=True)

        managed_path = Path(asset.project_path)
        self._assert_under(managed_path, managed_root)
        thumbnail_path = Path(asset.thumbnail_path) if asset.thumbnail_path else None
        if thumbnail_path is not None:
            self._assert_under(thumbnail_path, thumbnail_root)

        staged: list[tuple[Path, Path]] = []
        try:
            if managed_path.exists():
                stage_media = cache_root / f".remove-{asset.asset_id}{managed_path.suffix}"
                stage_media.unlink(missing_ok=True)
                os.replace(managed_path, stage_media)
                staged.append((stage_media, managed_path))
            if thumbnail_path is not None and thumbnail_path.exists():
                stage_thumb = cache_root / f".remove-{asset.asset_id}-thumbnail{thumbnail_path.suffix}"
                stage_thumb.unlink(missing_ok=True)
                os.replace(thumbnail_path, stage_thumb)
                staged.append((stage_thumb, thumbnail_path))
            try:
                self.repository.delete(asset.asset_id)
            except Exception:
                for stage, original in reversed(staged):
                    if stage.exists():
                        original.parent.mkdir(parents=True, exist_ok=True)
                        os.replace(stage, original)
                raise
            for stage, _ in staged:
                stage.unlink(missing_ok=True)
            self._remove_asset_cache(project_root, asset.asset_id)
            self.logger.info("Media removed: %s from project %s", asset.asset_id, project_id)
        except Exception as exc:
            if isinstance(exc, MediaServiceError):
                raise
            self.logger.exception("Could not remove media %s", asset.asset_id)
            raise MediaServiceError("This media item could not be removed safely.") from exc

    def duplicate_project_media(self, source: Project, duplicate: Project) -> int:
        return len(self.duplicate_project_media_map(source, duplicate))

    def duplicate_project_media_map(self, source: Project, duplicate: Project) -> dict[str, str]:
        source_root = Path(source.project_path).resolve()
        duplicate_root = Path(duplicate.project_path).resolve()
        assets = self.repository.list_by_project(source.project_id)
        mapping: dict[str, str] = {}
        for asset in assets:
            new_id = str(uuid4())
            source_managed = Path(asset.project_path)
            relative = self._relative_under(source_managed, source_root / "media")
            copied_managed = duplicate_root / "media" / relative
            new_managed = copied_managed.with_name(f"{new_id}{copied_managed.suffix}")
            if copied_managed.exists():
                new_managed.parent.mkdir(parents=True, exist_ok=True)
                copied_managed.replace(new_managed)

            new_thumbnail: Path | None = None
            if asset.thumbnail_path:
                source_thumb = Path(asset.thumbnail_path)
                thumb_relative = self._relative_under(source_thumb, source_root / "thumbnails")
                copied_thumb = duplicate_root / "thumbnails" / thumb_relative
                new_thumbnail = copied_thumb.with_name(f"{new_id}{copied_thumb.suffix or '.jpg'}")
                if copied_thumb.exists():
                    copied_thumb.replace(new_thumbnail)

            status = str(asset.status)
            if not new_managed.exists() and status == MediaStatus.READY.value:
                status = MediaStatus.MISSING.value
            clone = MediaAsset(
                asset_id=new_id,
                project_id=duplicate.project_id,
                media_type=asset.type,
                name=asset.name,
                original_path=asset.original_path,
                project_path=str(new_managed),
                thumbnail_path=str(new_thumbnail) if new_thumbnail and new_thumbnail.exists() else None,
                duration_ms=asset.duration_ms,
                width=asset.width,
                height=asset.height,
                fps=asset.fps,
                codec=asset.codec,
                audio_codec=asset.audio_codec,
                sample_rate=asset.sample_rate,
                channels=asset.channels,
                file_size=asset.file_size,
                mime_type=asset.mime_type,
                extension=asset.extension,
                created_at=asset.created_at,
                imported_at=media_utc_now_iso(),
                status=status,
                metadata_json=dict(asset.metadata_json),
            )
            self.repository.create(clone)
            mapping[asset.asset_id] = new_id
        return mapping

    @staticmethod
    def _media_directory(project_root: Path, media_type: str) -> Path:
        folder = {
            MediaType.VIDEO.value: "video",
            MediaType.AUDIO.value: "audio",
            MediaType.IMAGE.value: "images",
        }[media_type]
        return project_root / "media" / folder

    @staticmethod
    def _probe_image(path: Path) -> tuple[MediaProbeResult, dict[str, object]]:
        try:
            with Image.open(path) as image:
                image.verify()
            with Image.open(path) as image:
                oriented = ImageOps.exif_transpose(image)
                width, height = oriented.size
                image_format = image.format or path.suffix.lstrip(".").upper()
                orientation = None
                try:
                    orientation = image.getexif().get(274)
                except Exception:
                    orientation = None
        except (OSError, UnidentifiedImageError, ValueError) as exc:
            raise InvalidMediaError("The selected image is invalid or unsupported.") from exc
        return (
            MediaProbeResult(width=int(width), height=int(height)),
            {"image_format": str(image_format), "orientation": orientation},
        )

    def _require_project(self, project_id: str) -> Project:
        project = self.project_repository.get_by_id(project_id)
        if project is None:
            raise MediaProjectError("The current project could not be found.")
        return project

    @staticmethod
    def _emit_progress(callback: ProgressCallback | None, stage: str, fraction: float) -> None:
        if callback is not None:
            callback(stage, max(0.0, min(1.0, float(fraction))))

    @staticmethod
    def _raise_if_cancelled(cancellation: CancellationLike | None) -> None:
        if cancellation is not None and cancellation.is_cancelled:
            raise MediaImportCancelled("Import cancelled.")

    @staticmethod
    def _cleanup_import(destination: Path, thumbnail: Path) -> None:
        destination.unlink(missing_ok=True)
        destination.with_name(destination.name + ".part").unlink(missing_ok=True)
        thumbnail.unlink(missing_ok=True)
        thumbnail.with_name(thumbnail.name + ".part").unlink(missing_ok=True)

    @staticmethod
    def _assert_under(path: Path, root: Path) -> None:
        root_resolved = root.resolve()
        resolved = path.resolve(strict=False)
        if resolved == root_resolved:
            raise UnsafeMediaPathError("Refusing to operate on the managed media root itself.")
        try:
            resolved.relative_to(root_resolved)
        except ValueError as exc:
            raise UnsafeMediaPathError("Media path escapes the managed project directory.") from exc

    @classmethod
    def _relative_under(cls, path: Path, root: Path) -> Path:
        cls._assert_under(path, root)
        return path.resolve(strict=False).relative_to(root.resolve())

    @staticmethod
    def _remove_asset_cache(project_root: Path, asset_id: str) -> None:
        cache_root = project_root / "cache"
        if not cache_root.is_dir():
            return
        for candidate in cache_root.glob(f"{asset_id}*"):
            try:
                resolved = candidate.resolve(strict=False)
                resolved.relative_to(cache_root.resolve())
                if candidate.is_file() or candidate.is_symlink():
                    candidate.unlink(missing_ok=True)
                elif candidate.is_dir():
                    shutil.rmtree(candidate)
            except (OSError, ValueError):
                continue
