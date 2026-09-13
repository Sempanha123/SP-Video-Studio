from __future__ import annotations

from storage.migration_registry import MigrationRegistry, MigrationStep
from .v001_to_v002 import MIGRATION_ID, migrate


def registry():
    return MigrationRegistry((MigrationStep(1, 2, MIGRATION_ID, migrate),))
