from __future__ import annotations
import os
import shutil
from pathlib import Path
from uuid import uuid4

from domain.cache_errors import CacheMigrationFailed


class CacheMigrationService:
    """Copy-first cache-root migration. The old root stays authoritative until commit."""

    def __init__(self, cache_service, *, active_jobs: callable | None = None, logger=None) -> None:
        self.cache = cache_service
        self.active_jobs = active_jobs or (lambda: False)
        self.logger = logger

    def migrate(self, new_root: str | Path, *, mode: str = "move", delete_old_after_switch: bool = False, copier=None) -> Path:
        if self.active_jobs():
            raise CacheMigrationFailed("Cache location cannot be changed while a heavy job is using temporary files.")
        old = self.cache.root
        new = self.cache.validate_root(Path(new_root), create=False)
        if new == old:
            return old
        if mode not in {"move", "start_fresh"}:
            raise CacheMigrationFailed("Choose Move Existing Cache or Start Fresh.")
        new.parent.mkdir(parents=True, exist_ok=True)
        if new.exists() and any(new.iterdir()):
            raise CacheMigrationFailed("Choose an empty folder for the cache location.")
        if mode == "start_fresh":
            new.mkdir(parents=True, exist_ok=True)
            self.cache.set_cache_root(new)
            if delete_old_after_switch:
                self._delete_old(old)
            if self.logger: self.logger.info("Cache root switched fresh: %s -> %s", old, new)
            return new

        stage = new.parent / f".{new.name}.migration-{uuid4().hex}"
        copytree = copier or shutil.copytree
        try:
            if stage.exists(): shutil.rmtree(stage)
            if old.exists(): copytree(old, stage)
            else: stage.mkdir(parents=True, exist_ok=True)
            # destination remains untouched until staging is complete
            if new.exists(): new.rmdir()
            os.replace(stage, new)
            self.cache.set_cache_root(new)
            if delete_old_after_switch or mode == "move":
                self._delete_old(old)
            if self.logger: self.logger.info("Cache root migrated: %s -> %s", old, new)
            return new
        except Exception as exc:
            try:
                if stage.exists(): shutil.rmtree(stage)
            except OSError: pass
            # Preference/root is unchanged until set_cache_root above.
            if self.logger: self.logger.exception("Cache migration failed")
            if isinstance(exc, CacheMigrationFailed): raise
            raise CacheMigrationFailed("The cache could not be moved. The previous location is still valid.") from exc

    def _delete_old(self, old: Path) -> None:
        try:
            if old.exists() and old != self.cache.root:
                shutil.rmtree(old)
        except OSError as exc:
            # Switching succeeded; stale old cache is safe to leave behind.
            if self.logger: self.logger.warning("Old cache could not be removed after migration: %s", exc)
