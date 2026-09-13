from __future__ import annotations

from copy import deepcopy

from domain.schema_version import RECOVERY_SNAPSHOT_SCHEMA_VERSION


class RecoverySnapshotVersionError(RuntimeError):
    pass


class RecoveryMigrationService:
    def migrate_payload(self, payload: dict) -> tuple[dict, bool]:
        if not isinstance(payload, dict):
            raise RecoverySnapshotVersionError("Recovery snapshot payload is invalid.")
        data = deepcopy(payload)
        version = int(data.get("schemaVersion", data.get("schema_version", 1)) or 1)
        if version > RECOVERY_SNAPSHOT_SCHEMA_VERSION:
            raise RecoverySnapshotVersionError("Recovery snapshot was created by a newer SP Video Studio version.")
        changed = False
        if version == 1:
            data.setdefault("metadata", {})
            if isinstance(data["metadata"], dict):
                data["metadata"].setdefault("migratedFromRecoverySchema", 1)
            data["schemaVersion"] = 2
            changed = True
        return data, changed
