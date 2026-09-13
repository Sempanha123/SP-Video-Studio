from __future__ import annotations

from copy import deepcopy

from domain.schema_version import SETTINGS_SCHEMA_VERSION


class SettingsMigrationError(RuntimeError):
    pass


class SettingsMigrationService:
    """Pure settings-shape migration. Unknown keys are preserved verbatim."""

    def migrate(self, payload: dict) -> tuple[dict, bool]:
        if not isinstance(payload, dict):
            raise SettingsMigrationError("Settings payload must be an object.")
        data = deepcopy(payload)
        version = int(data.get("settings_version", 1) or 1)
        if version > SETTINGS_SCHEMA_VERSION:
            raise SettingsMigrationError("Settings were created by a newer SP Video Studio version.")
        changed = False
        while version < SETTINGS_SCHEMA_VERSION:
            if version == 1:
                data = self._v1_to_v2(data); version = 2; changed = True
            else:
                raise SettingsMigrationError(f"No settings migration exists from version {version}.")
        data["settings_version"] = SETTINGS_SCHEMA_VERSION
        return data, changed

    @staticmethod
    def _v1_to_v2(data: dict) -> dict:
        result = deepcopy(data)
        # Accept genuinely old flat names if encountered, but never discard unknown fields.
        projects = result.setdefault("projects", {}) if isinstance(result.get("projects", {}), dict) else {}
        if "project_root" in result and "default_projects_folder" not in projects:
            projects["default_projects_folder"] = result["project_root"]
        result["projects"] = projects
        performance = result.setdefault("performance", {}) if isinstance(result.get("performance", {}), dict) else {}
        if "performance_profile" in result and "profile" not in performance:
            performance["profile"] = result["performance_profile"]
        result["performance"] = performance
        shortcuts = result.setdefault("keyboard_shortcuts", {}) if isinstance(result.get("keyboard_shortcuts", {}), dict) else {}
        if "shortcuts" in result and "overrides" not in shortcuts and isinstance(result["shortcuts"], dict):
            shortcuts["overrides"] = deepcopy(result["shortcuts"])
        result["keyboard_shortcuts"] = shortcuts
        accessibility = result.setdefault("accessibility", {}) if isinstance(result.get("accessibility", {}), dict) else {}
        for old, new in (("reduce_motion", "reduce_motion"), ("interface_text_size", "interface_text_size"), ("stronger_focus_indicator", "stronger_focus_indicator")):
            if old in result and new not in accessibility:
                accessibility[new] = result[old]
        result["accessibility"] = accessibility
        result["settings_version"] = 2
        return result
