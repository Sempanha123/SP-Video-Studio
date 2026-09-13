from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any

from app.paths import AppPaths
from domain.settings import AppSettings
from services.settings_migration_service import SettingsMigrationError, SettingsMigrationService
from storage.repositories.settings_repository import SettingsRepository

class SettingsError(RuntimeError):pass
class InvalidSettingsPathError(SettingsError):pass

class SettingsService:
    def __init__(self,repository:SettingsRepository,paths:AppPaths,logger:logging.Logger|None=None)->None:
        self.repository=repository;self.paths=paths;self.logger=logger or logging.getLogger("sp_video_studio.settings");self.migrations=SettingsMigrationService();self._settings=self._load_or_initialize();self._apply_logging_level()
    @property
    def current(self)->AppSettings:return self._settings
    def reload(self)->AppSettings:self._settings=self._load_or_initialize();self._apply_logging_level();return self._settings
    def update(self,**changes:Any)->AppSettings:
        candidate=self._settings.with_changes(**changes)
        if "default_projects_folder" in changes:self.validate_directory(candidate.default_projects_folder,create=True)
        self.repository.save(candidate.to_dict());self._settings=candidate;self._apply_logging_level();return candidate
    def reset_defaults(self)->AppSettings:
        defaults=AppSettings.defaults(self.paths.default_projects_root);self.repository.save(defaults.to_dict());self._settings=defaults;self._apply_logging_level();return defaults
    def set_project_folder(self,path:str|Path)->AppSettings:
        target=self.validate_directory(path,create=True);return self.update(default_projects_folder=str(target))
    def validate_directory(self,path:str|Path,create:bool=False)->Path:
        target=Path(path).expanduser()
        if target.exists() and not target.is_dir():raise InvalidSettingsPathError("The selected path is not a folder.")
        if not target.exists():
            if not create:raise InvalidSettingsPathError("The selected folder does not exist.")
            try:target.mkdir(parents=True,exist_ok=True)
            except OSError as exc:raise InvalidSettingsPathError("The selected folder could not be created.") from exc
        if not os.access(target,os.W_OK):raise InvalidSettingsPathError("The selected folder is not writable.")
        try:
            probe=target/".sp-video-studio-write-test";probe.write_text("ok",encoding="utf-8");probe.unlink(missing_ok=True)
        except OSError as exc:raise InvalidSettingsPathError("The selected folder is not writable.") from exc
        return target.resolve()
    def _load_or_initialize(self)->AppSettings:
        defaults=AppSettings.defaults(self.paths.default_projects_root)
        try:
            payload=self.repository.load()
            if payload is None:self.repository.save(defaults.to_dict());return defaults
            migrated,changed=self.migrations.migrate(payload)
            settings=AppSettings.from_dict(migrated,self.paths.default_projects_root)
            if changed:self.repository.save(settings.to_dict());self.logger.info("Settings migrated to schema %d",settings.settings_version)
            return settings
        except SettingsMigrationError:
            # Newer settings are preserved; never overwrite/downgrade them silently.
            self.logger.exception("Settings schema is newer/unsupported; preserving file and using safe in-memory defaults")
            return defaults
        except Exception:
            self.logger.exception("Settings file is invalid; preserving it and restoring defaults")
            try:self.repository.quarantine_invalid()
            except OSError:self.logger.exception("Could not preserve invalid settings file")
            self.repository.save(defaults.to_dict());return defaults
    def _apply_logging_level(self)->None:
        level=logging.DEBUG if self._settings.debug_logging else logging.INFO;self.logger.setLevel(level)
        for handler in self.logger.handlers:handler.setLevel(level)
