from __future__ import annotations

from services.template_schema_migrator import TemplateSchemaMigrator


def migrate_payload(payload: dict) -> dict:
    """Central migration convention adapter around the existing Phase 24 migrator."""
    return TemplateSchemaMigrator().migrate(dict(payload))
