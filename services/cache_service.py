from __future__ import annotations
import hashlib
import json
import os
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Iterable, Iterator, Any

from domain.cache_entry import CacheEntry
from domain.cache_errors import CachePathUnsafe
from domain.storage_category import StorageCategory


_CACHE_DIRS: dict[StorageCategory, str] = {
    StorageCategory.PREVIEW_CACHE: "preview",
    StorageCategory.THUMBNAIL_CACHE: "thumbnails",
    StorageCategory.RENDER_TEMP: "render",
    StorageCategory.GENERATED_AUDIO: "audio",
    StorageCategory.AUDIO_WAVEFORM_CACHE: "audio/waveforms",
    StorageCategory.TRANSCRIPTION_TEMP: "transcription",
    StorageCategory.TRANSLATION_CACHE: "translation",
    StorageCategory.TEMPLATE_CACHE: "templates",
    StorageCategory.ASSET_THUMBNAIL_CACHE: "assets",
    StorageCategory.BATCH_INTERMEDIATE: "batch",
}
_DIR_CATEGORIES = {value: key for key, value in _CACHE_DIRS.items()}
_SETTINGS_FILE = "phase29_storage.json"
_MANIFEST = "cache_manifest.json"


def _iso_from_timestamp(value: float) -> str:
    return datetime.fromtimestamp(value, tz=timezone.utc).isoformat()


class CacheService:
    """Central Phase 29 cache-root/path/key/manifest service.

    All destructive users must still ask CleanupService; this object only resolves
    and scans app-owned cache paths. It intentionally never scans arbitrary user
    folders or shared package/model caches.
    """

    CACHE_VERSION = "29.1"

    def __init__(self, paths, *, logger=None, source_root: Path | None = None) -> None:
        self.paths = paths
        self.logger = logger
        self.source_root = Path(source_root or Path(__file__).resolve().parents[1]).resolve()
        self._prefs_path = Path(paths.settings) / _SETTINGS_FILE
        self._preferences = self._load_preferences()
        configured = str(self._preferences.get("cacheRoot") or "").strip()
        if configured:
            try:
                root = self.validate_root(Path(configured), create=False)
                object.__setattr__(self.paths, "cache", root)
            except Exception:
                # A tampered/stale preference must never make startup unsafe.
                fallback = (Path(paths.root) / "cache").expanduser().resolve(strict=False)
                object.__setattr__(self.paths, "cache", fallback)
                self._preferences["cacheRoot"] = str(fallback)
        self.ensure_structure()

    @property
    def root(self) -> Path:
        return Path(self.paths.cache).expanduser().resolve()

    @property
    def preferences(self) -> dict[str, Any]:
        defaults = {
            "cacheRoot": str(self.root),
            "maximumCacheBytes": 25 * 1024**3,
            "automaticCleanup": "balanced",
            "cleanupStaleTemp": True,
            "logRetentionDays": 14,
        }
        defaults.update(self._preferences)
        return defaults

    def update_preferences(self, **values: Any) -> dict[str, Any]:
        current = self.preferences
        for key in ("maximumCacheBytes", "logRetentionDays"):
            if key in values:
                current[key] = max(0, int(values[key]))
        if "automaticCleanup" in values:
            mode = str(values["automaticCleanup"])
            if mode not in {"off", "conservative", "balanced"}:
                raise ValueError("Automatic cleanup must be Off, Conservative, or Balanced.")
            current["automaticCleanup"] = mode
        if "cleanupStaleTemp" in values:
            current["cleanupStaleTemp"] = bool(values["cleanupStaleTemp"])
        self._preferences = current
        self._save_preferences()
        return self.preferences

    def set_cache_root(self, value: str | Path) -> Path:
        root = self.validate_root(Path(value), create=True)
        prefs = self.preferences
        prefs["cacheRoot"] = str(root)
        self._preferences = prefs
        self._save_preferences()
        object.__setattr__(self.paths, "cache", root)
        self.ensure_structure()
        return root

    def validate_root(self, value: Path, *, create: bool) -> Path:
        raw = Path(value).expanduser()
        if not raw.is_absolute():
            raise CachePathUnsafe("The selected cache folder must be an absolute path.")
        resolved = raw.resolve(strict=False)
        anchor = Path(resolved.anchor).resolve(strict=False) if resolved.anchor else None
        if not str(resolved).strip() or (anchor and resolved == anchor):
            raise CachePathUnsafe("A filesystem root cannot be used for cache storage.")
        if resolved == self.source_root or self._is_inside(resolved, self.source_root):
            raise CachePathUnsafe("The application source/executable folder cannot be used as cache storage.")
        if os.name == "nt":
            lowered = str(resolved).casefold().rstrip("\\/")
            windir = str(Path(os.environ.get("WINDIR", r"C:\Windows")).resolve(strict=False)).casefold().rstrip("\\/")
            program_files = [os.environ.get("ProgramFiles"), os.environ.get("ProgramFiles(x86)")]
            banned = [windir] + [str(Path(x).resolve(strict=False)).casefold().rstrip("\\/") for x in program_files if x]
            if any(lowered == item or lowered.startswith(item + "\\") for item in banned):
                raise CachePathUnsafe("Windows or Program Files folders cannot be used for cache storage.")
        # Never allow the settings/data root itself: cleanup must be isolated.
        app_root = Path(self.paths.root).expanduser().resolve(strict=False)
        if resolved == app_root:
            raise CachePathUnsafe("The application data root is too broad for cache storage.")
        if create:
            resolved.mkdir(parents=True, exist_ok=True)
        return resolved

    def ensure_structure(self) -> Path:
        self.root.mkdir(parents=True, exist_ok=True)
        for name in _CACHE_DIRS.values():
            (self.root / name).mkdir(parents=True, exist_ok=True)
        return self.root

    def category_root(self, category: StorageCategory | str) -> Path:
        key = category if isinstance(category, StorageCategory) else StorageCategory(str(category))
        if key not in _CACHE_DIRS:
            raise ValueError(f"{key.value} is not an application cache directory.")
        root = self.root / _CACHE_DIRS[key]
        root.mkdir(parents=True, exist_ok=True)
        return root

    def project_category_root(self, category: StorageCategory | str, project_id: str) -> Path:
        pid = self._safe_id(project_id)
        root = self.category_root(category) / pid
        root.mkdir(parents=True, exist_ok=True)
        return root

    def assert_contained(self, path: str | Path, root: str | Path | None = None) -> Path:
        base = Path(root or self.root).expanduser().resolve(strict=False)
        candidate = Path(path).expanduser()
        # lexical containment rejects ../../ before any filesystem action
        absolute = candidate if candidate.is_absolute() else base / candidate
        try:
            absolute.absolute().relative_to(base.absolute())
        except ValueError as exc:
            raise CachePathUnsafe("Cache path escapes the approved managed root.") from exc
        resolved = absolute.resolve(strict=False)
        try:
            resolved.relative_to(base)
        except ValueError as exc:
            raise CachePathUnsafe("Cache path resolves outside the approved managed root.") from exc
        return resolved

    def scan_entries(self, categories: Iterable[StorageCategory | str] | None = None, *, project_id: str = "") -> list[CacheEntry]:
        self.ensure_structure()
        selected = [StorageCategory(str(x.value if isinstance(x, StorageCategory) else x)) for x in categories] if categories else list(_CACHE_DIRS)
        rows: list[CacheEntry] = []
        for category in selected:
            root = self.category_root(category)
            scan_root = root
            if project_id:
                pid = self._safe_id(project_id)
                scan_root = root / pid
                if not scan_root.exists():
                    continue
            rows.extend(self._scan_files(scan_root, category, default_project_id=project_id))
        return rows

    def write_manifest(self, directory: str | Path, entry: CacheEntry | dict[str, Any]) -> Path:
        folder = self.assert_contained(directory)
        folder.mkdir(parents=True, exist_ok=True)
        data = entry.to_manifest() if isinstance(entry, CacheEntry) else dict(entry)
        data.setdefault("cacheVersion", self.CACHE_VERSION)
        target = folder / _MANIFEST
        temp = target.with_suffix(".tmp")
        temp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        os.replace(temp, target)
        return target

    def read_manifest(self, directory: str | Path) -> dict[str, Any] | None:
        try:
            folder = self.assert_contained(directory)
            data = json.loads((folder / _MANIFEST).read_text(encoding="utf-8"))
            return data if isinstance(data, dict) else None
        except (OSError, ValueError, json.JSONDecodeError, CachePathUnsafe):
            return None

    def stable_key(self, namespace: str, *parts: Any, version: str | None = None) -> str:
        payload = {"namespace": str(namespace), "version": str(version or self.CACHE_VERSION), "parts": parts}
        encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()

    def preview_key(self, *, source_fingerprint: str, scene_fingerprint: str, subtitle_fingerprint: str = "", audio_fingerprint: str = "", size: str = "") -> str:
        return self.stable_key("preview", source_fingerprint, scene_fingerprint, subtitle_fingerprint, audio_fingerprint, size)

    def thumbnail_key(self, media_fingerprint: str, requested_size: str | tuple[int, int], *, version: str = "1") -> str:
        return self.stable_key("thumbnail", media_fingerprint, requested_size, version=version)

    def regenerate_missing(self, path: str | Path, generator: Callable[[Path], Any], *, category: StorageCategory | str) -> Path:
        target = self.assert_contained(path, self.category_root(category))
        if target.exists():
            return target
        target.parent.mkdir(parents=True, exist_ok=True)
        generator(target)
        return target

    def invalidate(self, category: StorageCategory | str, *, project_id: str = "", source_fingerprint: str = "", predicate: Callable[[CacheEntry], bool] | None = None) -> list[Path]:
        invalid: list[Path] = []
        for entry in self.scan_entries([category], project_id=project_id):
            if source_fingerprint and entry.source_fingerprint != source_fingerprint:
                continue
            if predicate and not predicate(entry):
                continue
            invalid.append(entry.path)
        return invalid

    def _scan_files(self, root: Path, category: StorageCategory, *, default_project_id: str = "") -> Iterator[CacheEntry]:
        if not root.is_dir():
            return
        for current, dirs, files in os.walk(root, topdown=True, followlinks=False):
            base = Path(current)
            # Never traverse links/junction-like entries. Canonical delete checks still run later.
            dirs[:] = [name for name in dirs if not (base / name).is_symlink()]
            if category == StorageCategory.GENERATED_AUDIO and base == self.category_root(StorageCategory.GENERATED_AUDIO):
                dirs[:] = [name for name in dirs if name != "waveforms"]
            manifest = self.read_manifest(base) or {}
            for name in files:
                if name == _MANIFEST:
                    continue
                path = base / name
                if path.is_symlink():
                    # Keep it visible to cleanup planning so it is explicitly rejected as unsafe.
                    stat = path.lstat()
                else:
                    try:
                        stat = path.stat()
                    except OSError:
                        continue
                project = str(manifest.get("projectId") or default_project_id or self._project_from_path(path, category))
                yield CacheEntry(
                    path=path,
                    category=category,
                    project_id=project,
                    owner_id=str(manifest.get("ownerId") or manifest.get("jobId") or ""),
                    size_bytes=int(getattr(stat, "st_size", 0) or 0),
                    created_at=str(manifest.get("createdAt") or _iso_from_timestamp(getattr(stat, "st_ctime", stat.st_mtime))),
                    last_accessed_at=str(manifest.get("lastUsed") or _iso_from_timestamp(stat.st_mtime)),
                    regeneratable=bool(manifest.get("regeneratable", True)),
                    protected=bool(manifest.get("protected", False)),
                    origin=str(manifest.get("origin") or "filesystem_scan"),
                    source_fingerprint=str(manifest.get("sourceFingerprint") or ""),
                    cache_version=str(manifest.get("cacheVersion") or self.CACHE_VERSION),
                    metadata={k: v for k, v in manifest.items() if k not in {"projectId", "ownerId", "jobId", "createdAt", "lastUsed", "regeneratable", "protected", "origin", "sourceFingerprint", "cacheVersion"}},
                )

    def _project_from_path(self, path: Path, category: StorageCategory) -> str:
        root = self.category_root(category)
        try:
            rel = path.relative_to(root)
        except ValueError:
            return ""
        return rel.parts[0] if len(rel.parts) > 1 else ""

    def _load_preferences(self) -> dict[str, Any]:
        try:
            data = json.loads(self._prefs_path.read_text(encoding="utf-8"))
            return data if isinstance(data, dict) else {}
        except (OSError, json.JSONDecodeError):
            return {}

    def _save_preferences(self) -> None:
        self._prefs_path.parent.mkdir(parents=True, exist_ok=True)
        target = self._prefs_path
        temp = target.with_suffix(".tmp")
        payload = dict(self._preferences)
        payload["updatedAt"] = datetime.now(timezone.utc).isoformat()
        temp.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        os.replace(temp, target)

    @staticmethod
    def _safe_id(value: str) -> str:
        item = str(value or "").strip()
        if not item or item in {".", ".."} or "/" in item or "\\" in item:
            raise CachePathUnsafe("Cache owner/project identifier is unsafe.")
        return item

    @staticmethod
    def _is_inside(path: Path, root: Path) -> bool:
        try:
            path.relative_to(root)
            return True
        except ValueError:
            return False
