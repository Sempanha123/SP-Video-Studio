from __future__ import annotations

from sqlite3 import Connection


def _columns(connection: Connection, table: str) -> set[str]:
    return {str(row[1]) for row in connection.execute(f"PRAGMA table_info({table})").fetchall()}


def migrate(connection: Connection) -> None:
    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS voice_profiles (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            voice_type TEXT NOT NULL,
            language TEXT NOT NULL,
            category TEXT NOT NULL,
            engine_id TEXT NOT NULL,
            voice_description TEXT NOT NULL DEFAULT '',
            style_tags_json TEXT NOT NULL DEFAULT '[]',
            description TEXT NOT NULL DEFAULT '',
            reference_audio_path TEXT NOT NULL DEFAULT '',
            settings_json TEXT NOT NULL DEFAULT '{}',
            notes TEXT NOT NULL DEFAULT '',
            validated INTEGER NOT NULL DEFAULT 0,
            duration_ms INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS voice_preferences (
            voice_id TEXT PRIMARY KEY,
            favorite INTEGER NOT NULL DEFAULT 0,
            last_used_at TEXT,
            usage_count INTEGER NOT NULL DEFAULT 0
        );
        CREATE INDEX IF NOT EXISTS idx_voice_profiles_language ON voice_profiles(language);
        CREATE INDEX IF NOT EXISTS idx_voice_profiles_type ON voice_profiles(voice_type);
        CREATE INDEX IF NOT EXISTS idx_voice_profiles_category ON voice_profiles(category);
        """
    )
    if "default_voice_id" not in _columns(connection, "projects"):
        connection.execute("ALTER TABLE projects ADD COLUMN default_voice_id TEXT")
    if "voice_override_id" not in _columns(connection, "script_sections"):
        connection.execute("ALTER TABLE script_sections ADD COLUMN voice_override_id TEXT")
