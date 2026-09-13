from __future__ import annotations

from domain.migration_result import MigrationResult, MigrationStatus
from domain.schema_version import APP_SCHEMA_VERSION
from services.migration_validation_service import MigrationValidationService


class MigrationService:
    """Facade for application DB migration state/validation; SQLiteDatabase remains the executor."""
    def __init__(self, database, validation: MigrationValidationService | None = None) -> None:
        self.database = database
        self.validation = validation or MigrationValidationService()

    def ensure_application_current(self) -> MigrationResult:
        before = self.database.current_version()
        self.database.initialize()
        after = self.database.current_version()
        if after != APP_SCHEMA_VERSION:
            raise RuntimeError(f"Application database schema {after} is not supported by this build ({APP_SCHEMA_VERSION}).")
        with self.database.connect() as connection:
            self.validation.validate_database(connection, required_tables=("projects", "schema_migrations"))
        return MigrationResult(MigrationStatus.CURRENT if before == after else MigrationStatus.MIGRATED, before, after)
