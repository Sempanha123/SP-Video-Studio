from __future__ import annotations

import json
import shutil
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4

from services.safe_path_service import ManagedRoot, safe_delete
from storage.json_writer import atomic_write_json


@dataclass(frozen=True, slots=True)
class MigrationBackup:
    backup_id: str
    project_id: str
    root: Path
    database_path: Path
    metadata_path: Path | None
    created_at: str


class BackupService:
    """Backup only the shared SQLite DB + small metadata, never source media."""

    def __init__(self, database, backup_root: str | Path, logger=None) -> None:
        self.database = database
        self.backup_root = Path(backup_root).expanduser().resolve(strict=False)
        self.logger = logger
        self.backup_root.mkdir(parents=True, exist_ok=True)
        self._managed = ManagedRoot(self.backup_root, category="migration_backups")

    def create_project_backup(self, project_id: str, project_path: str | Path) -> MigrationBackup:
        stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
        backup_id = f"{stamp}-{str(project_id)[:8]}-{uuid4().hex[:8]}"
        root = self.backup_root / "projects" / backup_id
        root.mkdir(parents=True, exist_ok=False)
        database_path = root / "app.db"
        self.database.backup_to(database_path)
        source_metadata = Path(project_path) / "project.json"
        metadata_path: Path | None = None
        if source_metadata.is_file():
            metadata_path = root / "project.json"
            shutil.copy2(source_metadata, metadata_path)
        manifest = {
            "backupId": backup_id,
            "projectId": str(project_id),
            "createdAt": datetime.now(timezone.utc).isoformat(),
            "database": database_path.name,
            "metadata": metadata_path.name if metadata_path else "",
            "sourceMediaCopied": False,
            "protected": True,
        }
        atomic_write_json(root / "manifest.json", manifest)
        if self.logger:
            self.logger.info("Migration backup created: project=%s backup=%s", project_id, backup_id)
        return MigrationBackup(backup_id, str(project_id), root, database_path, metadata_path, manifest["createdAt"])

    def restore_project_backup(self, backup: MigrationBackup, live_database_path: str | Path, project_path: str | Path) -> None:
        # Restore is intended for startup/failure recovery before normal data use.
        source = Path(backup.database_path)
        target = Path(live_database_path)
        if not source.is_file():
            raise FileNotFoundError("Migration database backup is missing.")
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
        if backup.metadata_path and backup.metadata_path.is_file():
            shutil.copy2(backup.metadata_path, Path(project_path) / "project.json")

    def marker_path(self, project_id: str) -> Path:
        safe = "".join(ch for ch in str(project_id) if ch.isalnum() or ch in "-_" )[:96] or "project"
        return self.backup_root / "markers" / f"{safe}.json"

    def write_marker(self, project_id: str, payload: dict[str, object]) -> Path:
        path = self.marker_path(project_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        atomic_write_json(path, {**payload, "projectId": str(project_id), "migration_in_progress": True})
        return path

    def clear_marker(self, project_id: str) -> None:
        path = self.marker_path(project_id)
        if path.exists():
            safe_delete(path, self._managed, recursive=False)

    def read_marker(self, project_id: str) -> dict[str, object] | None:
        path = self.marker_path(project_id)
        if not path.is_file():
            return None
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
            return value if isinstance(value, dict) else None
        except (OSError, json.JSONDecodeError):
            return None

    def prune(self, *, keep: int = 3, minimum_age_days: int = 14) -> None:
        root = self.backup_root / "projects"
        if not root.is_dir():
            return
        rows = sorted((p for p in root.iterdir() if p.is_dir()), key=lambda p: p.stat().st_mtime, reverse=True)
        cutoff = datetime.now(timezone.utc) - timedelta(days=max(1, minimum_age_days))
        for index, path in enumerate(rows):
            if index < max(1, keep):
                continue
            if datetime.fromtimestamp(path.stat().st_mtime, timezone.utc) > cutoff:
                continue
            safe_delete(path, self._managed, recursive=True)
