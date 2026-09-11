from __future__ import annotations
import os
import time
from pathlib import Path
from typing import Callable, Iterable, Any

from domain.cache_errors import StorageScanFailed
from domain.storage_category import StorageCategory
from domain.storage_usage import ProjectStorageUsage, StorageUsage, readable_size


class StorageUsageService:
    """Filesystem-backed storage accounting with no external-file ownership inflation."""

    SUMMARY_TTL_SECONDS = 8.0

    def __init__(self, paths, cache_service, *, project_provider: Callable[[], Iterable[Any]] | None = None, asset_root_provider: Callable[[], Path | str | None] | None = None, external_asset_bytes_provider: Callable[[], int] | None = None, logger=None) -> None:
        self.paths = paths
        self.cache = cache_service
        self.project_provider = project_provider or (lambda: ())
        self.asset_root_provider = asset_root_provider or (lambda: getattr(paths, "assets", None))
        self.external_asset_bytes_provider = external_asset_bytes_provider or (lambda: 0)
        self.logger = logger
        self._cached: tuple[float, dict[str, Any]] | None = None

    def recalculate(self, *, force: bool = False) -> dict[str, Any]:
        now = time.monotonic()
        if not force and self._cached and now - self._cached[0] < self.SUMMARY_TTL_SECONDS:
            return self._cached[1]
        try:
            cache_rows = self.cache.scan_entries()
            cache_totals: dict[StorageCategory, StorageUsage] = {}
            for entry in cache_rows:
                usage = cache_totals.setdefault(entry.category, StorageUsage(entry.category))
                usage.size_bytes += entry.size_bytes
                usage.item_count += 1

            projects = self.project_usage()
            project_total = sum(x.total_bytes for x in projects)
            asset_root = self.asset_root_provider()
            asset_bytes = asset_count = asset_thumb_bytes = asset_thumb_count = 0
            if asset_root:
                asset_base = Path(asset_root)
                asset_total, asset_total_count = self._size_path(asset_base)
                asset_thumb_bytes, asset_thumb_count = self._size_path(asset_base / "thumbnails")
                asset_bytes = max(0, asset_total - asset_thumb_bytes)
                asset_count = max(0, asset_total_count - asset_thumb_count)
                if asset_thumb_bytes or asset_thumb_count:
                    thumb_usage = cache_totals.setdefault(StorageCategory.ASSET_THUMBNAIL_CACHE, StorageUsage(StorageCategory.ASSET_THUMBNAIL_CACHE))
                    thumb_usage.size_bytes += asset_thumb_bytes
                    thumb_usage.item_count += asset_thumb_count
            models_bytes, model_count = self._size_path(Path(self.paths.models))
            recovery_bytes, recovery_count = self._size_path(Path(getattr(self.paths, "recovery")))
            export_bytes, export_count = self._size_path(Path(getattr(self.paths, "exports")))
            logs_bytes, log_count = self._size_path(Path(self.paths.logs))
            cache_bytes = sum(x.size_bytes for x in cache_totals.values())

            categories = [
                StorageUsage(StorageCategory.PROJECT_DATA, project_total, len(projects)),
                StorageUsage(StorageCategory.ASSET_LIBRARY, asset_bytes, asset_count),
                *[cache_totals[k] for k in sorted(cache_totals, key=lambda x: x.value)],
                StorageUsage(StorageCategory.AI_MODELS, models_bytes, model_count),
                StorageUsage(StorageCategory.RECOVERY_DATA, recovery_bytes, recovery_count),
                StorageUsage(StorageCategory.FINAL_EXPORTS, export_bytes, export_count),
                StorageUsage(StorageCategory.LOGS, logs_bytes, log_count),
            ]
            external_bytes = max(0, int(self.external_asset_bytes_provider() or 0))
            if external_bytes:
                categories.append(StorageUsage(StorageCategory.EXTERNAL_REFERENCES, 0, 0, external_bytes=external_bytes))
            owned = project_total + asset_bytes + cache_bytes + models_bytes + recovery_bytes + export_bytes + logs_bytes
            result = {
                "totalOwnedBytes": owned,
                "totalOwnedDisplay": readable_size(owned),
                "cacheBytes": cache_bytes,
                "cacheDisplay": readable_size(cache_bytes),
                "externalReferencedBytes": external_bytes,
                "externalReferencedDisplay": readable_size(external_bytes),
                "categories": [x.to_dict() for x in categories],
                "projects": [x.to_dict() for x in projects],
                "cacheBreakdown": [cache_totals[x].to_dict() for x in cache_totals],
                "paths": {
                    "cache": str(self.cache.root),
                    "models": str(self.paths.models),
                    "recovery": str(getattr(self.paths, "recovery")),
                    "exports": str(getattr(self.paths, "exports")),
                    "assets": str(asset_root or ""),
                },
            }
            self._cached = (now, result)
            return result
        except Exception as exc:
            if self.logger:
                self.logger.exception("Storage scan failed")
            if isinstance(exc, StorageScanFailed):
                raise
            raise StorageScanFailed("Storage usage could not be calculated safely.") from exc

    def invalidate(self) -> None:
        self._cached = None

    def project_usage(self) -> list[ProjectStorageUsage]:
        rows: list[ProjectStorageUsage] = []
        for raw in list(self.project_provider() or ()):
            project_id = str(self._value(raw, "project_id", "id", "projectId") or "")
            name = str(self._value(raw, "name", "title") or project_id or "Project")
            root_value = self._value(raw, "folder", "path", "project_path", "projectPath", "root")
            if not root_value:
                continue
            root = Path(root_value)
            if not root.is_dir():
                continue
            usage = ProjectStorageUsage(project_id, name, str(root))
            media, _ = self._size_path(root / "media")
            audio, _ = self._size_path(root / "generated")
            if not audio:
                audio, _ = self._size_path(root / "audio")
            cache, _ = self._size_path(root / "cache")
            thumbs, _ = self._size_path(root / "thumbnails")
            renders, _ = self._size_path(root / "renders")
            usage.media_bytes = media
            usage.generated_audio_bytes = audio
            usage.cache_bytes = cache + thumbs
            usage.exports_bytes = renders
            total, _ = self._size_path(root)
            usage.project_data_bytes = max(0, total - media - audio - cache - thumbs - renders)
            rows.append(usage)
        rows.sort(key=lambda x: (-x.total_bytes, x.name.casefold()))
        return rows

    def _size_path(self, root: Path) -> tuple[int, int]:
        if not root.exists() or root.is_symlink():
            return 0, 0
        if root.is_file():
            try:
                return root.stat().st_size, 1
            except OSError:
                return 0, 0
        total = 0
        count = 0
        for current, dirs, files in os.walk(root, topdown=True, followlinks=False):
            base = Path(current)
            dirs[:] = [d for d in dirs if not (base / d).is_symlink()]
            for name in files:
                path = base / name
                if path.is_symlink():
                    continue
                try:
                    total += path.stat().st_size
                    count += 1
                except OSError:
                    continue
        return total, count

    @staticmethod
    def _value(item: Any, *names: str) -> Any:
        for name in names:
            if isinstance(item, dict) and name in item:
                return item[name]
            if hasattr(item, name):
                return getattr(item, name)
        return None
