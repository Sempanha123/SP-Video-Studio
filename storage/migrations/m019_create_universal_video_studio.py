from __future__ import annotations

from sqlite3 import Connection


def migrate(connection: Connection) -> None:
    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS speakers (
            id TEXT PRIMARY KEY,
            project_id TEXT NOT NULL,
            name TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'speaker',
            voice_id TEXT NOT NULL DEFAULT '',
            language TEXT NOT NULL DEFAULT 'en',
            description TEXT NOT NULL DEFAULT '',
            avatar TEXT NOT NULL DEFAULT '',
            metadata_json TEXT NOT NULL DEFAULT '{}',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY(project_id) REFERENCES projects(id) ON DELETE CASCADE
        );
        CREATE INDEX IF NOT EXISTS idx_speakers_project_role ON speakers(project_id, role, created_at);

        CREATE TABLE IF NOT EXISTS speech_blocks (
            id TEXT PRIMARY KEY,
            script_section_id TEXT NOT NULL,
            block_order INTEGER NOT NULL,
            speaker_id TEXT,
            text TEXT NOT NULL DEFAULT '',
            language TEXT NOT NULL DEFAULT 'en',
            voice_override_id TEXT NOT NULL DEFAULT '',
            speech_source_type TEXT NOT NULL DEFAULT 'tts',
            pause_before_ms INTEGER NOT NULL DEFAULT 0,
            pause_after_ms INTEGER NOT NULL DEFAULT 180,
            scene_id TEXT,
            start_offset_ms INTEGER,
            audio_id TEXT NOT NULL DEFAULT '',
            metadata_json TEXT NOT NULL DEFAULT '{}',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY(script_section_id) REFERENCES script_sections(id) ON DELETE CASCADE,
            FOREIGN KEY(speaker_id) REFERENCES speakers(id) ON DELETE SET NULL,
            FOREIGN KEY(scene_id) REFERENCES scenes(id) ON DELETE SET NULL
        );
        CREATE INDEX IF NOT EXISTS idx_speech_blocks_section_order ON speech_blocks(script_section_id, block_order);
        CREATE INDEX IF NOT EXISTS idx_speech_blocks_speaker ON speech_blocks(speaker_id);
        CREATE INDEX IF NOT EXISTS idx_speech_blocks_scene ON speech_blocks(scene_id, start_offset_ms);

        CREATE TABLE IF NOT EXISTS manual_audio_clips (
            id TEXT PRIMARY KEY,
            project_id TEXT NOT NULL,
            scene_id TEXT,
            media_id TEXT NOT NULL,
            start_ms INTEGER NOT NULL DEFAULT 0,
            duration_ms INTEGER NOT NULL,
            source_in_ms INTEGER NOT NULL DEFAULT 0,
            volume REAL NOT NULL DEFAULT 1,
            muted INTEGER NOT NULL DEFAULT 0,
            fade_in_ms INTEGER NOT NULL DEFAULT 0,
            fade_out_ms INTEGER NOT NULL DEFAULT 0,
            metadata_json TEXT NOT NULL DEFAULT '{}',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY(project_id) REFERENCES projects(id) ON DELETE CASCADE,
            FOREIGN KEY(scene_id) REFERENCES scenes(id) ON DELETE CASCADE,
            FOREIGN KEY(media_id) REFERENCES media_assets(id) ON DELETE CASCADE
        );
        CREATE INDEX IF NOT EXISTS idx_manual_audio_project_time ON manual_audio_clips(project_id,start_ms);
        CREATE INDEX IF NOT EXISTS idx_manual_audio_scene ON manual_audio_clips(scene_id,start_ms);

        CREATE TABLE IF NOT EXISTS phase22_project_state (
            project_id TEXT PRIMARY KEY,
            preview_quality TEXT NOT NULL DEFAULT 'auto',
            active_scene_id TEXT NOT NULL DEFAULT '',
            active_layer_id TEXT NOT NULL DEFAULT '',
            active_speaker_id TEXT NOT NULL DEFAULT '',
            metadata_json TEXT NOT NULL DEFAULT '{}',
            updated_at TEXT NOT NULL,
            FOREIGN KEY(project_id) REFERENCES projects(id) ON DELETE CASCADE
        );
        """
    )
