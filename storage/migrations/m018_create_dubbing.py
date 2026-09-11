from __future__ import annotations
from sqlite3 import Connection


def migrate(connection: Connection) -> None:
    connection.executescript('''
    CREATE TABLE IF NOT EXISTS dubbing_projects(
      project_id TEXT PRIMARY KEY,
      source_media_id TEXT,
      source_language TEXT NOT NULL DEFAULT 'auto',
      target_language TEXT NOT NULL DEFAULT 'km',
      transcript_id TEXT,
      translation_id TEXT,
      target_voice_id TEXT NOT NULL DEFAULT '',
      subtitle_track_id TEXT,
      status TEXT NOT NULL DEFAULT 'setup',
      settings_json TEXT NOT NULL DEFAULT '{}',
      metadata_json TEXT NOT NULL DEFAULT '{}',
      created_at TEXT NOT NULL,
      updated_at TEXT NOT NULL,
      FOREIGN KEY(project_id) REFERENCES projects(id) ON DELETE CASCADE,
      FOREIGN KEY(source_media_id) REFERENCES media_assets(id) ON DELETE SET NULL,
      FOREIGN KEY(transcript_id) REFERENCES transcripts(id) ON DELETE SET NULL,
      FOREIGN KEY(translation_id) REFERENCES translations(id) ON DELETE SET NULL,
      FOREIGN KEY(subtitle_track_id) REFERENCES subtitle_tracks(id) ON DELETE SET NULL
    );
    CREATE INDEX IF NOT EXISTS idx_dubbing_projects_source ON dubbing_projects(source_media_id);

    CREATE TABLE IF NOT EXISTS dub_segments(
      id TEXT PRIMARY KEY,
      project_id TEXT NOT NULL,
      source_transcript_segment_id TEXT,
      translation_segment_id TEXT,
      segment_order INTEGER NOT NULL,
      source_start_ms INTEGER NOT NULL,
      source_end_ms INTEGER NOT NULL,
      target_text TEXT NOT NULL DEFAULT '',
      voice_id TEXT NOT NULL DEFAULT '',
      generated_audio_id TEXT,
      generated_audio_path TEXT NOT NULL DEFAULT '',
      generated_duration_ms INTEGER NOT NULL DEFAULT 0,
      timing_mode TEXT NOT NULL DEFAULT 'natural',
      timing_status TEXT NOT NULL DEFAULT 'not_generated',
      audio_status TEXT NOT NULL DEFAULT 'pending',
      start_offset_ms INTEGER NOT NULL DEFAULT 0,
      stretch_factor REAL NOT NULL DEFAULT 1.0,
      locked INTEGER NOT NULL DEFAULT 0,
      user_modified INTEGER NOT NULL DEFAULT 0,
      speaker_label TEXT NOT NULL DEFAULT '',
      source_hash TEXT NOT NULL DEFAULT '',
      generation_hash TEXT NOT NULL DEFAULT '',
      metadata_json TEXT NOT NULL DEFAULT '{}',
      created_at TEXT NOT NULL,
      updated_at TEXT NOT NULL,
      FOREIGN KEY(project_id) REFERENCES dubbing_projects(project_id) ON DELETE CASCADE,
      FOREIGN KEY(source_transcript_segment_id) REFERENCES transcript_segments(id) ON DELETE SET NULL,
      FOREIGN KEY(translation_segment_id) REFERENCES translation_segments(id) ON DELETE SET NULL,
      FOREIGN KEY(generated_audio_id) REFERENCES generated_audio(id) ON DELETE SET NULL
    );
    CREATE UNIQUE INDEX IF NOT EXISTS idx_dub_segments_project_translation ON dub_segments(project_id,translation_segment_id) WHERE translation_segment_id IS NOT NULL;
    CREATE INDEX IF NOT EXISTS idx_dub_segments_project_order ON dub_segments(project_id,segment_order);
    CREATE INDEX IF NOT EXISTS idx_dub_segments_audio_status ON dub_segments(project_id,audio_status);

    CREATE TABLE IF NOT EXISTS dub_audio_outputs(
      id TEXT PRIMARY KEY,
      project_id TEXT NOT NULL,
      source_media_id TEXT,
      target_language TEXT NOT NULL,
      voice_profile_id TEXT NOT NULL DEFAULT '',
      file_path TEXT NOT NULL,
      duration_ms INTEGER NOT NULL DEFAULT 0,
      fingerprint TEXT NOT NULL DEFAULT '',
      output_type TEXT NOT NULL DEFAULT 'final_mix',
      status TEXT NOT NULL DEFAULT 'ready',
      settings_json TEXT NOT NULL DEFAULT '{}',
      metadata_json TEXT NOT NULL DEFAULT '{}',
      created_at TEXT NOT NULL,
      FOREIGN KEY(project_id) REFERENCES dubbing_projects(project_id) ON DELETE CASCADE,
      FOREIGN KEY(source_media_id) REFERENCES media_assets(id) ON DELETE SET NULL
    );
    CREATE INDEX IF NOT EXISTS idx_dub_audio_outputs_project ON dub_audio_outputs(project_id,created_at);

    CREATE TABLE IF NOT EXISTS dub_mix_settings(
      project_id TEXT PRIMARY KEY,
      mode TEXT NOT NULL DEFAULT 'duck',
      original_volume REAL NOT NULL DEFAULT 0.25,
      dub_volume REAL NOT NULL DEFAULT 1.0,
      duck_normal_volume REAL NOT NULL DEFAULT 0.25,
      duck_under_volume REAL NOT NULL DEFAULT 0.12,
      duck_fade_ms INTEGER NOT NULL DEFAULT 120,
      metadata_json TEXT NOT NULL DEFAULT '{}',
      updated_at TEXT NOT NULL,
      FOREIGN KEY(project_id) REFERENCES dubbing_projects(project_id) ON DELETE CASCADE
    );
    ''')
