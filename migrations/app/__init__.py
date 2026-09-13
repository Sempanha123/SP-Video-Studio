from __future__ import annotations

from storage.migration_registry import MigrationRegistry, MigrationStep


def registry():
    """Adapter over the existing storage.migrations list; does not duplicate SQL migrations."""
    from storage.migrations import MIGRATIONS
    return MigrationRegistry(tuple(MigrationStep(m.version - 1, m.version, f"app_{m.version:03d}_{m.name}", m.apply, getattr(m, "validate", None)) for m in MIGRATIONS))
