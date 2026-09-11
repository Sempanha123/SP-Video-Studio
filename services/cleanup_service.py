from __future__ import annotations
import os
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Iterable, Any

from domain.cache_entry import CacheEntry
from domain.cache_errors import CacheCleanupFailed, CacheEntryActive, CacheEntryProtected, CachePathUnsafe
from domain.cleanup_policy import CleanupPlan, CleanupResult
from domain.storage_category import StorageCategory, StorageSafety, cache_categories, definition


class CleanupService:
    """Plans and executes conservative app-owned cleanup.

    Contract before delete: classify -> containment -> active ownership -> protection
    -> delete -> result. Recovery, models, final exports, project data/media and
    external references are never accepted as Clear Cache categories.
    """

    def __init__(self, cache_service, paths, *, active_checker: Callable[[Path, CacheEntry], bool] | None = None, generated_audio_referenced: Callable[[Path, str], bool] | None = None, recovery_veto: Callable[[Path], bool] | None = None, project_provider: Callable[[], Iterable[Any]] | None = None, asset_root_provider: Callable[[], Path | str | None] | None = None, current_log_provider: Callable[[], Path | None] | None = None, logger=None) -> None:
        self.cache = cache_service
        self.paths = paths
        self.active_checker = active_checker or (lambda _path, _entry: False)
        self.generated_audio_referenced = generated_audio_referenced or (lambda _path, _project_id: False)
        self.recovery_veto = recovery_veto or (lambda _path: False)
        self.project_provider = project_provider or (lambda: ())
        self.asset_root_provider = asset_root_provider or (lambda: getattr(paths, "assets", None))
        self.current_log_provider = current_log_provider or (lambda: None)
        self.logger = logger

    def preview_cleanup(self, categories: Iterable[StorageCategory | str] | None = None, *, project_id: str = "", stale_before: float | None = None, reason: str = "manual") -> CleanupPlan:
        selected = [StorageCategory(str(x.value if isinstance(x, StorageCategory) else x)) for x in (categories or cache_categories())]
        plan = CleanupPlan(reason=reason)
        for category in selected:
            rule = definition(category)
            if rule.safety not in {StorageSafety.SAFE_TO_CLEAR, StorageSafety.REGENERATABLE}:
                plan.skipped_protected.append(category.value)
                continue
            for entry in self._entries_for(category, project_id=project_id):
                if stale_before is not None:
                    try:
                        mtime = entry.path.lstat().st_mtime
                    except OSError:
                        continue
                    if mtime >= stale_before:
                        continue
                verdict = self._candidate_reason(entry)
                if verdict == "active":
                    plan.skipped_active.append(str(entry.path))
                elif verdict == "protected":
                    plan.skipped_protected.append(str(entry.path))
                elif verdict == "unsafe":
                    plan.skipped_unsafe.append(str(entry.path))
                else:
                    plan.add(entry)
        return plan

    def clear_all_cache(self, *, dry_run: bool = False) -> CleanupPlan | CleanupResult:
        plan = self.preview_cleanup(cache_categories(), reason="clear_all_cache")
        return plan if dry_run else self.execute(plan)

    def clear_categories(self, categories: Iterable[StorageCategory | str], *, dry_run: bool = False, project_id: str = "") -> CleanupPlan | CleanupResult:
        plan = self.preview_cleanup(categories, project_id=project_id, reason="selected_categories")
        return plan if dry_run else self.execute(plan)

    def clear_project_cache(self, project_id: str, *, include_unreferenced_audio: bool = True, dry_run: bool = False) -> CleanupPlan | CleanupResult:
        pid = str(project_id or "").strip()
        categories = [StorageCategory.PREVIEW_CACHE, StorageCategory.THUMBNAIL_CACHE, StorageCategory.RENDER_TEMP, StorageCategory.TRANSCRIPTION_TEMP, StorageCategory.TRANSLATION_CACHE, StorageCategory.TEMPLATE_CACHE, StorageCategory.BATCH_INTERMEDIATE]
        if include_unreferenced_audio:
            categories.append(StorageCategory.GENERATED_AUDIO)
        plan = self.preview_cleanup(categories, project_id=pid, reason="project_cache")
        # Legacy project-local cache/thumbnail/temp folders predate Phase29 root.
        project = self._project(pid)
        root = self._project_root(project)
        if root:
            for folder, category in (("cache", StorageCategory.PREVIEW_CACHE), ("thumbnails", StorageCategory.THUMBNAIL_CACHE)):
                base = root / folder
                plan = self._add_managed_tree(plan, base, category, pid, root)
            render_temp = root / "renders" / ".temp"
            plan = self._add_managed_tree(plan, render_temp, StorageCategory.RENDER_TEMP, pid, root)
            if include_unreferenced_audio:
                # Only explicitly temporary/unreferenced generated files are candidates.
                for candidate in (root / "generated" / "cache", root / "audio" / "cache"):
                    plan = self._add_managed_tree(plan, candidate, StorageCategory.GENERATED_AUDIO, pid, root)
        return plan if dry_run else self.execute(plan)


    def orphan_plan(self, *, existing_project_ids: set[str] | None = None, minimum_age_seconds: int = 24 * 3600) -> CleanupPlan:
        existing = {str(x) for x in (existing_project_ids or {_pid for _pid in (str(self._value(p, "project_id", "id", "projectId") or "") for p in list(self.project_provider() or ())) if _pid})}
        cutoff = datetime.now(timezone.utc).timestamp() - max(0, int(minimum_age_seconds))
        plan = CleanupPlan(reason="orphan_cache")
        for entry in self.cache.scan_entries():
            if not entry.project_id or entry.project_id in existing:
                continue
            try: mtime = entry.path.lstat().st_mtime
            except OSError: continue
            if mtime > cutoff: continue
            verdict = self._candidate_reason(entry)
            if verdict == "ok": plan.add(entry)
            elif verdict == "active": plan.skipped_active.append(str(entry.path))
            elif verdict == "unsafe": plan.skipped_unsafe.append(str(entry.path))
            else: plan.skipped_protected.append(str(entry.path))
        return plan

    def execute(self, plan: CleanupPlan) -> CleanupResult:
        result = CleanupResult(
            skipped_active=list(plan.skipped_active),
            skipped_protected=list(plan.skipped_protected),
            skipped_unsafe=list(plan.skipped_unsafe),
        )
        if self.logger:
            self.logger.info("Cache cleanup started: reason=%s entries=%d estimated=%d", plan.reason, len(plan.entries), plan.estimated_bytes)
        for entry in plan.entries:
            verdict = self._candidate_reason(entry)
            if verdict == "active":
                result.skipped_active.append(str(entry.path)); continue
            if verdict == "protected":
                result.skipped_protected.append(str(entry.path)); continue
            if verdict == "unsafe":
                result.skipped_unsafe.append(str(entry.path)); continue
            try:
                path = self._approved_path(entry)
                before = entry.size_bytes
                if path.is_dir() and not path.is_symlink():
                    shutil.rmtree(path)
                else:
                    path.unlink(missing_ok=True)
                result.freed_bytes += max(0, before)
                result.deleted.append(str(path))
                self._remove_empty_parents(path.parent)
            except (OSError, PermissionError) as exc:
                result.failed.append({"path": str(entry.path), "error": str(exc)})
            except CachePathUnsafe:
                result.skipped_unsafe.append(str(entry.path))
        if self.logger:
            self.logger.info("Cache cleanup completed: freed=%d deleted=%d active=%d failed=%d", result.freed_bytes, len(result.deleted), len(result.skipped_active), len(result.failed))
        return result

    def lru_plan(self, *, maximum_bytes: int, entries: Iterable[CacheEntry] | None = None) -> CleanupPlan:
        limit = max(0, int(maximum_bytes))
        candidates = list(entries if entries is not None else self.cache.scan_entries())
        current = sum(max(0, x.size_bytes) for x in candidates)
        plan = CleanupPlan(reason="cache_limit_lru")
        if limit <= 0 or current <= limit:
            return plan
        eligible: list[CacheEntry] = []
        for entry in candidates:
            verdict = self._candidate_reason(entry)
            if verdict == "active": plan.skipped_active.append(str(entry.path))
            elif verdict in {"protected", "unsafe"}:
                (plan.skipped_unsafe if verdict == "unsafe" else plan.skipped_protected).append(str(entry.path))
            else: eligible.append(entry)
        eligible.sort(key=lambda x: (x.last_accessed_at or x.created_at, x.created_at, str(x.path)))
        need = current - limit
        for entry in eligible:
            if plan.estimated_bytes >= need:
                break
            plan.add(entry)
        return plan

    def cleanup_old_logs(self, *, retention_days: int = 14, dry_run: bool = False) -> CleanupPlan | CleanupResult:
        cutoff = datetime.now(timezone.utc).timestamp() - max(1, int(retention_days)) * 86400
        plan = CleanupPlan(reason="old_logs")
        root = Path(self.paths.logs).resolve(strict=False)
        current = self.current_log_provider()
        current = Path(current).resolve(strict=False) if current else None
        if root.is_dir():
            for path in root.iterdir():
                if not path.is_file() or path.is_symlink():
                    continue
                if current and path.resolve(strict=False) == current:
                    plan.skipped_active.append(str(path)); continue
                try: stat = path.stat()
                except OSError: continue
                if stat.st_mtime >= cutoff: continue
                plan.add(CacheEntry(path, StorageCategory.LOGS, size_bytes=stat.st_size, regeneratable=True, origin="log_retention"))
        return plan if dry_run else self.execute(plan)

    def _candidate_reason(self, entry: CacheEntry) -> str:
        rule = definition(entry.category)
        if entry.protected or rule.safety in {StorageSafety.PROTECTED, StorageSafety.USER_DATA, StorageSafety.EXTERNAL}:
            return "protected"
        if entry.path.is_symlink():
            return "unsafe"
        try:
            self._approved_path(entry)
        except CachePathUnsafe:
            return "unsafe"
        if self.recovery_veto(entry.path):
            return "protected"
        if self.active_checker(entry.path, entry):
            return "active"
        if entry.category == StorageCategory.GENERATED_AUDIO and self.generated_audio_referenced(entry.path, entry.project_id):
            return "protected"
        return "ok"

    def _approved_path(self, entry: CacheEntry) -> Path:
        if entry.category == StorageCategory.LOGS:
            return self._assert_inside(entry.path, Path(self.paths.logs))
        root_text = str(entry.metadata.get("managedRoot") or "")
        if root_text:
            return self._assert_inside(entry.path, Path(root_text))
        if entry.origin == "project_local":
            raise CachePathUnsafe("Project cache entry has no managed root.")
        return self.cache.assert_contained(entry.path)

    def _entries_for(self, category: StorageCategory, *, project_id: str) -> list[CacheEntry]:
        if category == StorageCategory.LOGS:
            plan = self.cleanup_old_logs(dry_run=True)
            return list(plan.entries)
        try:
            rows = self.cache.scan_entries([category], project_id=project_id)
        except ValueError:
            rows = []
        # Phase 25 stores generated Asset Library thumbnails under the managed
        # asset root. They are disposable, but the sibling source assets are not.
        if category == StorageCategory.ASSET_THUMBNAIL_CACHE and not project_id:
            asset_root = self.asset_root_provider()
            if asset_root:
                thumbs = Path(asset_root).expanduser().resolve(strict=False) / "thumbnails"
                rows.extend(self._managed_tree_entries(thumbs, category, "", thumbs))
        return rows

    def _managed_tree_entries(self, base: Path, category: StorageCategory, project_id: str, managed_root: Path) -> list[CacheEntry]:
        rows: list[CacheEntry] = []
        if not base.exists() or base.is_symlink():
            return rows
        try:
            self._assert_inside(base, managed_root)
        except CachePathUnsafe:
            return rows
        for current, dirs, files in os.walk(base, topdown=True, followlinks=False):
            current_path = Path(current)
            safe_dirs = []
            for name in dirs:
                child = current_path / name
                if child.is_symlink():
                    try: stat = child.lstat()
                    except OSError: continue
                    rows.append(CacheEntry(child, category, project_id=project_id, size_bytes=int(stat.st_size), regeneratable=True, origin="managed_cache", metadata={"managedRoot": str(managed_root)}))
                else:
                    safe_dirs.append(name)
            dirs[:] = safe_dirs
            for name in files:
                path = current_path / name
                try: stat = path.lstat() if path.is_symlink() else path.stat()
                except OSError: continue
                rows.append(CacheEntry(path, category, project_id=project_id, size_bytes=int(stat.st_size), regeneratable=True, origin="managed_cache", metadata={"managedRoot": str(managed_root)}))
        return rows

    def _add_managed_tree(self, plan: CleanupPlan, base: Path, category: StorageCategory, project_id: str, project_root: Path) -> CleanupPlan:
        if not base.exists() or base.is_symlink():
            return plan
        try:
            self._assert_inside(base, project_root)
        except CachePathUnsafe:
            plan.skipped_unsafe.append(str(base)); return plan
        for current, dirs, files in os.walk(base, topdown=True, followlinks=False):
            current_path = Path(current)
            dirs[:] = [x for x in dirs if not (current_path / x).is_symlink()]
            for name in files:
                path = current_path / name
                if path.is_symlink():
                    plan.skipped_unsafe.append(str(path)); continue
                try: stat = path.stat()
                except OSError: continue
                entry = CacheEntry(path, category, project_id=project_id, size_bytes=stat.st_size, regeneratable=True, origin="project_local", metadata={"managedRoot": str(project_root)})
                verdict = self._candidate_reason(entry)
                if verdict == "ok": plan.add(entry)
                elif verdict == "active": plan.skipped_active.append(str(path))
                elif verdict == "unsafe": plan.skipped_unsafe.append(str(path))
                else: plan.skipped_protected.append(str(path))
        return plan

    def _project(self, project_id: str):
        for item in list(self.project_provider() or ()):
            pid = str(self._value(item, "project_id", "id", "projectId") or "")
            if pid == project_id:
                return item
        return None

    def _project_root(self, item: Any) -> Path | None:
        if item is None: return None
        raw = self._value(item, "folder", "path", "project_path", "projectPath", "root")
        return Path(raw).resolve(strict=False) if raw else None

    def _remove_empty_parents(self, start: Path) -> None:
        root = self.cache.root
        current = start
        while current != root:
            try:
                current.relative_to(root)
            except ValueError:
                return
            try:
                current.rmdir()
            except OSError:
                return
            current = current.parent

    @staticmethod
    def _assert_inside(path: Path, root: Path) -> Path:
        base = Path(root).expanduser().resolve(strict=False)
        raw = Path(path).expanduser()
        absolute = raw if raw.is_absolute() else base / raw
        try: absolute.absolute().relative_to(base.absolute())
        except ValueError as exc: raise CachePathUnsafe("Path escapes its managed root.") from exc
        resolved = absolute.resolve(strict=False)
        try: resolved.relative_to(base)
        except ValueError as exc: raise CachePathUnsafe("Path resolves outside its managed root.") from exc
        return resolved

    @staticmethod
    def _value(item: Any, *names: str):
        for name in names:
            if isinstance(item, dict) and name in item: return item[name]
            if hasattr(item, name): return getattr(item, name)
        return None
