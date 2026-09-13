from __future__ import annotations

"""Phase 38 migration layer over completed Phase 37 security/privacy runtime."""
import types
import app.phase31_runtime as p31
from app.phase37_runtime import run as run_phase37
from app.paths import AppPaths
from services.backup_service import BackupService
from services.migration_service import MigrationService
from services.migration_validation_service import MigrationValidationService
from services.project_migration_service import ProjectMigrationService
from services.recovery_migration_service import RecoveryMigrationService
from services.settings_migration_service import SettingsMigrationService


def run()->int:
    original_install=p31._install
    installed={'done':False}
    def install(container):
        result=original_install(container)
        if installed['done']:return result
        try:
            from storage.database import SQLiteDatabase
            from storage.repositories.project_repository import ProjectRepository
            from services.project_service import ProjectService
            database=container.resolve(SQLiteDatabase);projects=container.resolve(ProjectRepository);project_service=container.resolve(ProjectService)
            try:paths=container.resolve(AppPaths)
            except Exception:paths=AppPaths.discover();paths.ensure()
            logger=container.resolve('logger')
            validation=MigrationValidationService();backups=BackupService(database,paths.data/'migration_backups',logger)
            migrations=MigrationService(database,validation);project_migrations=ProjectMigrationService(database,projects,backups,validation,logger)
            for cls,obj in ((MigrationValidationService,validation),(BackupService,backups),(MigrationService,migrations),(ProjectMigrationService,project_migrations),(SettingsMigrationService,SettingsMigrationService()),(RecoveryMigrationService,RecoveryMigrationService())):
                try:container.register_instance(cls,obj)
                except Exception:pass
            if not getattr(project_service,'_phase38_migration_wrapped',False):
                original_open=project_service.open_project;original_duplicate=project_service.duplicate_project
                def ensure_then_open(self,project_id):
                    project_migrations.ensure_current(project_id)
                    return original_open(project_id)
                def ensure_then_duplicate(self,project_id):
                    project_migrations.ensure_current(project_id)
                    return original_duplicate(project_id)
                project_service.open_project=types.MethodType(ensure_then_open,project_service)
                project_service.duplicate_project=types.MethodType(ensure_then_duplicate,project_service)
                project_service._phase38_migration_wrapped=True
        except Exception:
            # Startup DB migrations already ran before this layer; registration failures must not create a second bootstrap path.
            pass
        installed['done']=True
        return result
    p31._install=install
    try:return run_phase37()
    finally:p31._install=original_install
