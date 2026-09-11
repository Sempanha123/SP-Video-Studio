from __future__ import annotations

from domain.model_installation import ModelInstallation
from domain.project import utc_now_iso
from storage.database import SQLiteDatabase


class ModelRepository:
    def __init__(self, database: SQLiteDatabase) -> None:
        self.database = database

    def get(self, model_id: str) -> ModelInstallation | None:
        with self.database.connect() as connection:
            row = connection.execute(
                "SELECT * FROM model_installations WHERE model_id = ?", (model_id,)
            ).fetchone()
        return ModelInstallation.from_record(row) if row else None

    def list_all(self) -> list[ModelInstallation]:
        with self.database.connect() as connection:
            rows = connection.execute(
                "SELECT * FROM model_installations ORDER BY updated_at DESC, model_id"
            ).fetchall()
        return [ModelInstallation.from_record(row) for row in rows]

    def upsert(self, installation: ModelInstallation) -> ModelInstallation:
        installation.updated_at = utc_now_iso()
        values = installation.to_record()
        with self.database.connect() as connection, connection:
            connection.execute(
                """
                INSERT INTO model_installations(
                    model_id, installed, status, install_path, installed_version,
                    downloaded_bytes, total_bytes, installed_at, verified_at,
                    verification_status, error_message, is_loaded, in_use_count,
                    metadata_json, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(model_id) DO UPDATE SET
                    installed = excluded.installed,
                    status = excluded.status,
                    install_path = excluded.install_path,
                    installed_version = excluded.installed_version,
                    downloaded_bytes = excluded.downloaded_bytes,
                    total_bytes = excluded.total_bytes,
                    installed_at = excluded.installed_at,
                    verified_at = excluded.verified_at,
                    verification_status = excluded.verification_status,
                    error_message = excluded.error_message,
                    is_loaded = excluded.is_loaded,
                    in_use_count = excluded.in_use_count,
                    metadata_json = excluded.metadata_json,
                    updated_at = excluded.updated_at
                """,
                values,
            )
        return installation

    def remove(self, model_id: str) -> None:
        with self.database.connect() as connection, connection:
            connection.execute("DELETE FROM model_installations WHERE model_id = ?", (model_id,))
