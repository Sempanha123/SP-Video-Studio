from __future__ import annotations

from sqlite3 import Connection


def _columns(connection: Connection, table: str) -> set[str]:
    return {str(row[1]) for row in connection.execute(f"PRAGMA table_info({table})").fetchall()}


def migrate(connection: Connection) -> None:
    cols = _columns(connection, "speech_blocks")
    additions = (
        ("project_id", "TEXT NOT NULL DEFAULT ''"),
        ("timeline_start_ms", "INTEGER"),
        ("timeline_end_ms", "INTEGER"),
        ("active_generated_audio_id", "TEXT NOT NULL DEFAULT ''"),
        ("text_hash", "TEXT NOT NULL DEFAULT ''"),
        ("audio_status", "TEXT NOT NULL DEFAULT 'not_generated'"),
        ("timing_status", "TEXT NOT NULL DEFAULT 'not_generated'"),
        ("user_modified", "INTEGER NOT NULL DEFAULT 0"),
    )
    for name, ddl in additions:
        if name not in cols:
            connection.execute(f"ALTER TABLE speech_blocks ADD COLUMN {name} {ddl}")

    # Backfill project ownership and keep Phase 22 audio pointers compatible.
    connection.execute(
        """UPDATE speech_blocks SET project_id=COALESCE((
               SELECT sc.project_id FROM script_sections s JOIN scripts sc ON sc.id=s.script_id
               WHERE s.id=speech_blocks.script_section_id
           ), project_id) WHERE project_id=''"""
    )
    connection.execute(
        "UPDATE speech_blocks SET active_generated_audio_id=audio_id WHERE active_generated_audio_id='' AND audio_id<>''"
    )
    connection.execute(
        "UPDATE speech_blocks SET audio_status='ready' WHERE active_generated_audio_id<>'' AND audio_status='not_generated'"
    )
    connection.execute(
        "UPDATE speech_blocks SET timeline_start_ms=start_offset_ms WHERE timeline_start_ms IS NULL AND scene_id IS NULL AND start_offset_ms IS NOT NULL"
    )
    connection.executescript(
        """
        CREATE INDEX IF NOT EXISTS idx_speech_blocks_project_timing
            ON speech_blocks(project_id, timeline_start_ms, timeline_end_ms, block_order);
        CREATE INDEX IF NOT EXISTS idx_speech_blocks_project_status
            ON speech_blocks(project_id, audio_status, block_order);
        CREATE INDEX IF NOT EXISTS idx_generated_audio_speech_section
            ON generated_audio(project_id, section_id, created_at);
        """
    )
