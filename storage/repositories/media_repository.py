from __future__ import annotations

import json

from domain.media import MediaAsset
from storage.database import SQLiteDatabase


SORT_SQL = {
    "recent": "imported_at DESC, name COLLATE NOCASE ASC",
    "name": "name COLLATE NOCASE ASC, imported_at DESC",
    "type": "type ASC, name COLLATE NOCASE ASC",
    "size": "file_size DESC, name COLLATE NOCASE ASC",
}


class MediaRepository:
    def __init__(self, database: SQLiteDatabase) -> None:
        self.database = database

    def create(self, asset: MediaAsset) -> MediaAsset:
        asset.validate()
        with self.database.connect() as connection, connection:
            connection.execute(
                """
                INSERT INTO media_assets(
                    id, project_id, type, name, original_path, project_path,
                    thumbnail_path, duration_ms, width, height, fps, codec,
                    audio_codec, sample_rate, channels, file_size, mime_type,
                    extension, created_at, imported_at, status, metadata_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                self._values(asset),
            )
        return asset

    def get_by_id(self, asset_id: str) -> MediaAsset | None:
        with self.database.connect() as connection:
            row = connection.execute(
                "SELECT * FROM media_assets WHERE id = ?", (asset_id,)
            ).fetchone()
        return MediaAsset.from_record(row) if row else None

    def list_by_project(
        self,
        project_id: str,
        *,
        search: str = "",
        media_type: str = "all",
        sort: str = "recent",
    ) -> list[MediaAsset]:
        clauses = ["project_id = ?"]
        params: list[object] = [project_id]
        if media_type and media_type != "all":
            clauses.append("type = ?")
            params.append(media_type)
        if search.strip():
            clauses.append("LOWER(name) LIKE ? ESCAPE '\\'")
            params.append(f"%{self._escape_like(search.strip().lower())}%")
        order = SORT_SQL.get(sort, SORT_SQL["recent"])
        sql = f"SELECT * FROM media_assets WHERE {' AND '.join(clauses)} ORDER BY {order}"
        with self.database.connect() as connection:
            rows = connection.execute(sql, tuple(params)).fetchall()
        return [MediaAsset.from_record(row) for row in rows]

    def count_for_project(self, project_id: str) -> int:
        with self.database.connect() as connection:
            row = connection.execute(
                "SELECT COUNT(*) AS count FROM media_assets WHERE project_id = ?",
                (project_id,),
            ).fetchone()
        return int(row["count"] if row else 0)

    def update(self, asset: MediaAsset) -> MediaAsset:
        asset.validate()
        with self.database.connect() as connection, connection:
            cursor = connection.execute(
                """
                UPDATE media_assets SET
                    project_id = ?, type = ?, name = ?, original_path = ?, project_path = ?,
                    thumbnail_path = ?, duration_ms = ?, width = ?, height = ?, fps = ?,
                    codec = ?, audio_codec = ?, sample_rate = ?, channels = ?, file_size = ?,
                    mime_type = ?, extension = ?, created_at = ?, imported_at = ?, status = ?,
                    metadata_json = ?
                WHERE id = ?
                """,
                self._update_values(asset),
            )
            if cursor.rowcount == 0:
                raise KeyError(f"Media asset {asset.asset_id} does not exist.")
        return asset

    def update_status(self, asset_id: str, status: str) -> None:
        with self.database.connect() as connection, connection:
            cursor = connection.execute(
                "UPDATE media_assets SET status = ? WHERE id = ?",
                (status, asset_id),
            )
            if cursor.rowcount == 0:
                raise KeyError(f"Media asset {asset_id} does not exist.")

    def delete(self, asset_id: str) -> None:
        with self.database.connect() as connection, connection:
            cursor = connection.execute("DELETE FROM media_assets WHERE id = ?", (asset_id,))
            if cursor.rowcount == 0:
                raise KeyError(f"Media asset {asset_id} does not exist.")

    def delete_for_project(self, project_id: str) -> None:
        with self.database.connect() as connection, connection:
            connection.execute("DELETE FROM media_assets WHERE project_id = ?", (project_id,))

    @staticmethod
    def _escape_like(value: str) -> str:
        return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")

    @staticmethod
    def _values(asset: MediaAsset) -> tuple[object, ...]:
        return (
            asset.asset_id,
            asset.project_id,
            asset.type,
            asset.name,
            asset.original_path,
            asset.project_path,
            asset.thumbnail_path,
            asset.duration_ms,
            asset.width,
            asset.height,
            asset.fps,
            asset.codec,
            asset.audio_codec,
            asset.sample_rate,
            asset.channels,
            asset.file_size,
            asset.mime_type,
            asset.extension,
            asset.created_at,
            asset.imported_at,
            str(asset.status),
            json.dumps(asset.metadata_json, ensure_ascii=False, separators=(",", ":")),
        )

    @classmethod
    def _update_values(cls, asset: MediaAsset) -> tuple[object, ...]:
        values = cls._values(asset)
        return values[1:] + (asset.asset_id,)
